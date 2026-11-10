# liumcode.com

Unofficial Lium referral code site (`LIUM-ZQQPPE1W`) with live GPU prices.

- `build.py` (Python stdlib only) fetches https://lium.io/pricing.json and writes the site to `dist/`.
  If the fetch fails it uses `data/pricing-fallback.json`.
- GitHub Actions builds and deploys to GitHub Pages on push, every 3 hours, and on manual dispatch.

Local build: `python3 build.py`, then open `dist/index.html`.

## Prayer counter API (`api/`)

`/pray` on the site talks to `https://api.liumcode.com/pray`, a tiny Go service on the server
(not on GitHub Pages). `GET` returns `{"count":N}`; `POST {"n":1-50}` from origin `https://liumcode.com` adds prayers.
Per-IP click buckets in the app plus an nginx request limit; nginx only accepts Cloudflare-proxied traffic,
and the service listens on 127.0.0.1:9985 only.

Deploy: `cd api && go test ./... && CGO_ENABLED=0 go build -trimpath -ldflags "-s -w" -o /usr/local/bin/pray-counter . && systemctl restart pray-counter`
(unit file in `api/deploy/`, count stored in `/var/lib/private/pray-counter/count`).
