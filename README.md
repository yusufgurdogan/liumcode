# liumcode.com

Unofficial Lium referral code site (`LIUM-ZQQPPE1W`) with live GPU prices.

- `build.py` (Python stdlib only) fetches https://lium.io/pricing.json and writes the site to `dist/`.
  If the fetch fails it uses `data/pricing-fallback.json`.
- GitHub Actions builds and deploys to GitHub Pages on push, every 3 hours, and on manual dispatch.

Local build: `python3 build.py`, then open `dist/index.html`.
