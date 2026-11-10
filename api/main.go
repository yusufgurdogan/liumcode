// pray-counter: one global "prayers for cheaper GPUs" counter for liumcode.com.
//
//	GET  /pray            -> {"count":N}
//	POST /pray  {"n":k}   -> {"count":N,"accepted":a}   (1 <= k <= maxBatch)
//
// Meant to sit behind nginx on localhost, which sets X-Real-IP. Each IP gets a
// token bucket of clicks (fast human clicking passes, scripts get capped), and
// there is a global cap too. The count is saved to a small file.
package main

import (
	"encoding/json"
	"errors"
	"flag"
	"log"
	"net"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"time"
)

const (
	maxBatch    = 50    // clicks per request
	bucketSize  = 150.0 // clicks an IP can burst
	refillPerS  = 12.0  // sustained clicks per second per IP (fast human clicking)
	globalPerS  = 3000.0
	maxTracked  = 200000 // IPs kept in memory
	idleForget  = 15 * time.Minute
	saveEvery   = 5 * time.Second
	maxBodySize = 256
)

type bucket struct {
	tokens float64
	last   time.Time
}

type server struct {
	mu      sync.Mutex
	count   uint64
	dirty   bool
	ips     map[string]*bucket
	global  bucket
	origins map[string]bool
	file    string
}

func take(b *bucket, now time.Time, rate, size, want float64) float64 {
	b.tokens += now.Sub(b.last).Seconds() * rate
	if b.tokens > size {
		b.tokens = size
	}
	b.last = now
	got := want
	if got > b.tokens {
		got = float64(int(b.tokens))
	}
	if got < 0 {
		got = 0
	}
	b.tokens -= got
	return got
}

func (s *server) add(ip string, n int) (uint64, int) {
	now := time.Now()
	s.mu.Lock()
	defer s.mu.Unlock()
	b := s.ips[ip]
	if b == nil {
		if len(s.ips) >= maxTracked {
			return s.count, 0 // under a flood of new IPs, stop counting rather than grow memory
		}
		b = &bucket{tokens: bucketSize, last: now}
		s.ips[ip] = b
	}
	got := take(b, now, refillPerS, bucketSize, float64(n))
	if got > 0 {
		g := take(&s.global, now, globalPerS, globalPerS, got)
		b.tokens += got - g // give back what the global cap refused
		got = g
	}
	a := int(got)
	if a > 0 {
		s.count += uint64(a)
		s.dirty = true
	}
	return s.count, a
}

func (s *server) get() uint64 {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.count
}

func (s *server) janitor() {
	for range time.Tick(time.Minute) {
		cut := time.Now().Add(-idleForget)
		s.mu.Lock()
		for ip, b := range s.ips {
			if b.last.Before(cut) {
				delete(s.ips, ip)
			}
		}
		s.mu.Unlock()
	}
}

func (s *server) load() error {
	b, err := os.ReadFile(s.file)
	if errors.Is(err, os.ErrNotExist) {
		return nil
	}
	if err != nil {
		return err
	}
	n, err := strconv.ParseUint(strings.TrimSpace(string(b)), 10, 64)
	if err != nil {
		return err
	}
	s.count = n
	return nil
}

func (s *server) save() {
	s.mu.Lock()
	if !s.dirty {
		s.mu.Unlock()
		return
	}
	n := s.count
	s.dirty = false
	s.mu.Unlock()
	tmp := s.file + ".tmp"
	if err := os.WriteFile(tmp, []byte(strconv.FormatUint(n, 10)+"\n"), 0o600); err != nil {
		log.Printf("save: %v", err)
		s.mu.Lock()
		s.dirty = true
		s.mu.Unlock()
		return
	}
	if err := os.Rename(tmp, s.file); err != nil {
		log.Printf("save: %v", err)
	}
}

func clientIP(r *http.Request) string {
	if ip := strings.TrimSpace(r.Header.Get("X-Real-IP")); net.ParseIP(ip) != nil {
		// Group IPv6 by /64 so one host can't rotate through its whole prefix.
		if p := net.ParseIP(ip); p.To4() == nil {
			return p.Mask(net.CIDRMask(64, 128)).String()
		}
		return ip
	}
	host, _, _ := net.SplitHostPort(r.RemoteAddr)
	return host
}

func (s *server) handle(w http.ResponseWriter, r *http.Request) {
	h := w.Header()
	h.Set("Content-Type", "application/json")
	h.Set("Cache-Control", "no-store")
	h.Set("X-Content-Type-Options", "nosniff")
	origin := r.Header.Get("Origin")
	if s.origins[origin] {
		h.Set("Access-Control-Allow-Origin", origin)
		h.Set("Vary", "Origin")
	}
	switch r.Method {
	case http.MethodOptions:
		h.Set("Access-Control-Allow-Methods", "GET, POST")
		h.Set("Access-Control-Allow-Headers", "Content-Type")
		h.Set("Access-Control-Max-Age", "86400")
		w.WriteHeader(http.StatusNoContent)
	case http.MethodGet, http.MethodHead:
		json.NewEncoder(w).Encode(map[string]uint64{"count": s.get()})
	case http.MethodPost:
		if !s.origins[origin] {
			http.Error(w, `{"error":"forbidden"}`, http.StatusForbidden)
			return
		}
		var body struct {
			N int `json:"n"`
		}
		dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, maxBodySize))
		if err := dec.Decode(&body); err != nil || body.N < 1 || body.N > maxBatch {
			http.Error(w, `{"error":"n must be 1-50"}`, http.StatusBadRequest)
			return
		}
		n, a := s.add(clientIP(r), body.N)
		json.NewEncoder(w).Encode(map[string]any{"count": n, "accepted": a})
	default:
		h.Set("Allow", "GET, POST, OPTIONS")
		http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
	}
}

func main() {
	listen := flag.String("listen", "127.0.0.1:9985", "listen address")
	state := flag.String("state", ".", "state directory")
	origins := flag.String("origins", "https://liumcode.com", "comma-separated allowed origins")
	flag.Parse()

	s := &server{ips: map[string]*bucket{}, origins: map[string]bool{},
		file: filepath.Join(*state, "count"), global: bucket{tokens: globalPerS, last: time.Now()}}
	for _, o := range strings.Split(*origins, ",") {
		if o = strings.TrimSpace(o); o != "" {
			s.origins[o] = true
		}
	}
	if err := s.load(); err != nil {
		log.Fatalf("load %s: %v", s.file, err)
	}
	go s.janitor()
	go func() {
		for range time.Tick(saveEvery) {
			s.save()
		}
	}()

	mux := http.NewServeMux()
	mux.HandleFunc("/pray", s.handle)
	srv := &http.Server{Addr: *listen, Handler: mux, ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout: 10 * time.Second, WriteTimeout: 10 * time.Second, IdleTimeout: 60 * time.Second,
		MaxHeaderBytes: 8 << 10}

	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)
	go func() {
		<-stop
		srv.Close()
	}()
	log.Printf("pray-counter on %s, count %d", *listen, s.count)
	if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		log.Fatal(err)
	}
	s.save()
}
