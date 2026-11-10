package main

import (
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func newTest(t *testing.T) *server {
	return &server{ips: map[string]*bucket{}, origins: map[string]bool{"https://liumcode.com": true},
		file: filepath.Join(t.TempDir(), "count"), global: bucket{tokens: globalPerS, last: time.Now()}}
}

func do(s *server, method, origin, body string) *httptest.ResponseRecorder {
	r := httptest.NewRequest(method, "/pray", strings.NewReader(body))
	r.Header.Set("Origin", origin)
	r.Header.Set("X-Real-IP", "203.0.113.7")
	w := httptest.NewRecorder()
	s.handle(w, r)
	return w
}

func TestPray(t *testing.T) {
	s := newTest(t)
	if w := do(s, "POST", "https://liumcode.com", `{"n":5}`); w.Code != 200 || !strings.Contains(w.Body.String(), `"count":5`) {
		t.Fatal(w.Code, w.Body)
	}
	if w := do(s, "POST", "https://evil.example", `{"n":5}`); w.Code != 403 {
		t.Fatal("foreign origin allowed", w.Code)
	}
	for _, b := range []string{`{"n":0}`, `{"n":51}`, `{"n":-3}`, `nope`, `{"n":` + strings.Repeat("9", 400) + `}`} {
		if w := do(s, "POST", "https://liumcode.com", b); w.Code != 400 {
			t.Fatal("bad body accepted", b, w.Code)
		}
	}
	if w := do(s, "GET", "", ""); !strings.Contains(w.Body.String(), `"count":5`) {
		t.Fatal(w.Body)
	}
}

func TestRateLimit(t *testing.T) {
	s := newTest(t)
	total := 0
	for i := 0; i < 20; i++ { // 1000 clicks instantly from one IP
		n, a := s.add("1.2.3.4", 50)
		total = a + total
		_ = n
	}
	if total != int(bucketSize) {
		t.Fatalf("burst accepted %d, want %d", total, int(bucketSize))
	}
	if _, a := s.add("5.6.7.8", 50); a != 50 { // other IPs unaffected
		t.Fatal("other ip limited", a)
	}
}

func TestSaveLoad(t *testing.T) {
	s := newTest(t)
	s.add("1.2.3.4", 42)
	s.save()
	b, _ := os.ReadFile(s.file)
	s2 := newTest(t)
	s2.file = s.file
	if err := s2.load(); err != nil || s2.count != 42 {
		t.Fatal(string(b), err, s2.count)
	}
}

func TestIPv6Grouping(t *testing.T) {
	r := httptest.NewRequest("GET", "/pray", nil)
	r.Header.Set("X-Real-IP", "2001:db8:1:2:aaaa::1")
	r2 := httptest.NewRequest("GET", "/pray", nil)
	r2.Header.Set("X-Real-IP", "2001:db8:1:2:bbbb::9")
	if clientIP(r) != clientIP(r2) {
		t.Fatal("same /64 not grouped")
	}
}

func TestPrayHTTP(t *testing.T) {
	s := newTest(t)
	ts := httptest.NewServer(http.HandlerFunc(s.handle))
	defer ts.Close()
	res, err := http.Get(ts.URL)
	if err != nil || res.Header.Get("Cache-Control") != "no-store" {
		t.Fatal(err)
	}
}
