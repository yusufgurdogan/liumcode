#!/usr/bin/env python3
"""Build the static Lium referral site into ./dist.

Stdlib only. Fetches live prices from Lium's public feed and falls back to
data/pricing-fallback.json when the fetch fails.
"""
import datetime as dt
import html
import json
import os
import shutil
import sys
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")

DOMAIN = os.environ.get("SITE_DOMAIN", "liumcode.com")
BASE = f"https://{DOMAIN}"
CODE = "LIUM-ZQQPPE1W"
SIGNUP = f"https://lium.io/register?ref={CODE}"
PRICING_URL = "https://lium.io/pricing.json"
FALLBACK = os.path.join(ROOT, "data", "pricing-fallback.json")
SITE_NAME = "Lium Referral Code"
INDEXNOW_KEY = "5c1e8a4f7b3d4e2a9f6c0b1d8e7a3c42"

e = html.escape


# ---------------------------------------------------------------- data

def load_pricing():
    try:
        req = urllib.request.Request(PRICING_URL, headers={"User-Agent": "lium-referral-site-builder/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
        if not data.get("models"):
            raise ValueError("no models in feed")
        with open(FALLBACK, "w") as f:
            json.dump(data, f)
        print(f"fetched live pricing: {len(data['models'])} models", file=sys.stderr)
        return data, True
    except Exception as ex:  # network or format problem: build from the snapshot
        print(f"pricing fetch failed ({ex}); using fallback", file=sys.stderr)
        with open(FALLBACK) as f:
            return json.load(f), False


def usd(v):
    if v is None:
        return "–"
    s = f"{v:.2f}"
    if abs(v * 100 - round(v * 100)) > 1e-9:
        s = f"{v:.3f}"
    return f"${s}"


def price_range(m):
    lo, hi = m["min_price_usd_per_gpu_hour"], m["max_price_usd_per_gpu_hour"]
    return usd(lo) if lo == hi else f"{usd(lo)}–{usd(hi)}"


ARCH = {"blackwell": "Blackwell", "hopper": "Hopper", "ampere": "Ampere", "ada": "Ada Lovelace",
        "ada lovelace": "Ada Lovelace", "volta": "Volta", "turing": "Turing"}
CLASS = {"datacenter": "Data center", "professional": "Workstation", "consumer": "Consumer"}


# ---------------------------------------------------------------- layout

CSS = """
:root{--bg:#0b0d12;--panel:#12151d;--panel2:#181c26;--line:#262b38;--text:#e6e8ee;--muted:#9aa1b2;
--accent:#7c5cff;--accent2:#a48bff;--ok:#3ecf8e;--warn:#f0b429;--radius:12px}
@media (prefers-color-scheme: light){:root:not([data-theme="dark"]){--bg:#f7f7fb;--panel:#fff;--panel2:#f0f0f6;
--line:#dfe1ea;--text:#151821;--muted:#5b6275;--accent:#5b3df5;--accent2:#5b3df5;--ok:#11875a;--warn:#a86b00}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--text);font:16px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--accent2)}
.wrap{max-width:960px;margin:0 auto;padding:0 16px}
header.top{border-bottom:1px solid var(--line)}
header.top .wrap{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:4px 12px;min-height:56px;padding-top:8px;padding-bottom:8px}
.brand{font-weight:700;color:var(--text);text-decoration:none}
.brand span{color:var(--accent2)}
nav{display:flex;gap:16px;flex-wrap:wrap}
nav a{color:var(--muted);text-decoration:none;font-size:15px}
nav a:hover{color:var(--text)}
h1{font-size:clamp(28px,5vw,42px);line-height:1.15;margin:40px 0 12px;letter-spacing:-.02em}
h2{font-size:24px;margin:48px 0 12px;letter-spacing:-.01em}
h3{font-size:18px;margin:24px 0 6px}
.lead{color:var(--muted);font-size:18px;max-width:680px}
.codebox{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:20px;margin:24px 0;
display:flex;flex-wrap:wrap;align-items:center;gap:12px}
.codebox .label{width:100%;color:var(--muted);font-size:14px}
.code{font:700 clamp(22px,4.5vw,30px)/1.2 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.04em;
background:var(--panel2);border:1px dashed var(--accent);border-radius:8px;padding:10px 16px;user-select:all}
.btn{display:inline-block;border:0;border-radius:8px;padding:12px 18px;font:600 15px system-ui,sans-serif;cursor:pointer;
text-decoration:none;background:var(--accent);color:#fff}
.btn.ghost{background:transparent;color:var(--text);border:1px solid var(--line)}
.btn:hover{filter:brightness(1.1)}
.small{font-size:13px;color:var(--muted)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:16px 0}
.card{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:16px}
.card b{display:block;font-size:22px}
.card span{color:var(--muted);font-size:14px}
ol.steps{padding-left:20px}
ol.steps li{margin:6px 0}
.tablewrap{overflow-x:auto;border:1px solid var(--line);border-radius:var(--radius)}
table{border-collapse:collapse;width:100%;font-size:15px;background:var(--panel)}
th,td{text-align:left;padding:10px 12px;border-bottom:1px solid var(--line);white-space:nowrap}
th{color:var(--muted);font-weight:600;font-size:13px;background:var(--panel2)}
tr:last-child td{border-bottom:0}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.pill{display:inline-block;font-size:12px;padding:1px 8px;border-radius:99px;border:1px solid var(--line);color:var(--muted)}
.pill.ok{color:var(--ok);border-color:var(--ok)}
details{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:12px 16px;margin:8px 0}
summary{cursor:pointer;font-weight:600}
.note{border-left:3px solid var(--warn);padding:8px 12px;background:var(--panel);border-radius:0 8px 8px 0;font-size:14px;color:var(--muted)}
footer{border-top:1px solid var(--line);margin-top:64px;padding:24px 0 40px;color:var(--muted);font-size:13px}
.crumbs{font-size:14px;color:var(--muted);margin-top:24px}
.crumbs a{color:var(--muted)}
"""

COPY_JS = """
<script>
document.querySelectorAll('[data-copy]').forEach(function(b){b.addEventListener('click',function(){
var t=b.getAttribute('data-copy');var done=function(){var o=b.textContent;b.textContent='Copied!';setTimeout(function(){b.textContent=o},1500)};
if(navigator.clipboard){navigator.clipboard.writeText(t).then(done,function(){})}else{var r=document.createRange();
var el=document.querySelector('.code');r.selectNodeContents(el);var s=getSelection();s.removeAllRanges();s.addRange(r);document.execCommand('copy');done()}
})});
</script>
"""


def canonical(path):
    return BASE + ("/" if path == "index.html" else "/" + path.replace(".html", ""))


def breadcrumbs(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": u}
                                for i, (n, u) in enumerate(items)]}


# Set by main(): whether share images were generated, and when prices were fetched.
STATE = {"images": False, "modified": None}


def page(path, title, desc, body, jsonld=None, og=None, og_alt=None, crumbs=None, noindex=False):
    canon = canonical(path)
    docs = list(jsonld or [])
    if crumbs:
        docs.append(breadcrumbs(crumbs))
    if not noindex:
        docs.append({"@context": "https://schema.org", "@type": "WebPage", "url": canon, "name": title,
                     "description": desc, "inLanguage": "en", "dateModified": STATE["modified"],
                     "isPartOf": {"@type": "WebSite", "name": SITE_NAME, "url": BASE + "/"}})
    ld = "".join('<script type="application/ld+json">' + json.dumps(x, ensure_ascii=False).replace("</", "<\\/")
                 + "</script>" for x in docs)
    img = ""
    if STATE["images"]:
        og = og or "/og/home.png"
        img = f"""<meta property="og:image" content="{BASE}{og}">
<meta property="og:image:type" content="image/png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{e(og_alt or title)}">
<meta name="twitter:image" content="{BASE}{og}">
<meta name="twitter:image:alt" content="{e(og_alt or title)}">"""
    robots = "noindex" if noindex else "index,follow,max-image-preview:large,max-snippet:-1"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<meta name="robots" content="{robots}">
<link rel="canonical" href="{canon}">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:locale" content="en_US">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{canon}">
<meta name="twitter:card" content="{'summary_large_image' if STATE['images'] else 'summary'}">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(desc)}">
{img}
<link rel="icon" href="/favicon.ico" sizes="48x48">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<meta name="theme-color" content="#0b0d12">
<style>{CSS}</style>
{ld}
</head>
<body>
<header class="top"><div class="wrap">
<a class="brand" href="/">Lium <span>Referral Code</span></a>
<nav><a href="/#prices">GPU prices</a><a href="/free-credits">Free credits</a><a href="/#faq">FAQ</a></nav>
</div></header>
<main class="wrap">
{body}
</main>
<footer><div class="wrap">
<p>Unofficial site. Not affiliated with, endorsed by or operated by Lium or Datura AI Corp. “Lium” is used only to describe the service.</p>
<p>Disclosure: {e(CODE)} is our referral code. If you sign up with it, Lium pays us a share of your top-ups. It costs you nothing.</p>
<p>Prices come from Lium's public price feed and change constantly. Check lium.io before you rent.</p>
</div></footer>
{COPY_JS}
</body>
</html>
"""


def codebox(label="Your Lium referral code"):
    return f"""<div class="codebox">
<div class="label">{e(label)}</div>
<span class="code">{e(CODE)}</span>
<button class="btn ghost" data-copy="{e(CODE)}">Copy code</button>
<a class="btn" href="{e(SIGNUP)}" rel="nofollow sponsored">Sign up with this code →</a>
<div class="small" style="width:100%">The signup link fills the code in for you. If it doesn't, paste it into the “Referral code” field.</div>
</div>"""


def price_table(models, updated):
    rows = []
    for m in models:
        avail = m["available_gpus"]
        status = (f'<span class="pill ok">{avail} free</span>' if avail else '<span class="pill">sold out</span>')
        rows.append(f"""<tr><td><a href="/gpu/{e(m['slug'])}">{e(m['name'])}</a></td>
<td class="num">{m['vram_gb']} GB</td><td class="num">{price_range(m)}</td><td>{status}</td></tr>""")
    return f"""<div class="tablewrap"><table>
<thead><tr><th>GPU</th><th class="num">VRAM</th><th class="num">$ / GPU / hour</th><th>Now</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>
<p class="small">From Lium's public price feed, {e(updated)}. Ranges are live asks from different providers; sold-out models show the last known price.</p>"""


def faq_html(items):
    return "".join(f"<details><summary>{e(q)}</summary><p>{a}</p></details>" for q, a in items)


def faq_ld(items):
    import re
    strip = lambda s: re.sub(r"<[^>]+>", "", s)
    return {"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": q,
                            "acceptedAnswer": {"@type": "Answer", "text": strip(a)}} for q, a in items]}


# ---------------------------------------------------------------- pages

def build_index(data, models, updated, year):
    fleet = data.get("fleet", {})
    avail = [m for m in models if m["available_gpus"] > 0]
    cheapest = min(avail, key=lambda m: m["min_price_usd_per_gpu_hour"]) if avail else None
    h100 = next((m for m in models if m["slug"].startswith("h100-80gb")), None)

    faq = [
        ("What is the Lium referral code?",
         f"<b>{e(CODE)}</b>. Enter it in the “Referral code” field when you create your Lium account, or use "
         f'<a href="{e(SIGNUP)}" rel="nofollow sponsored">this signup link</a>, which fills it in.'),
        ("Does the referral code give me a discount?",
         "No. Lium doesn't advertise an extra bonus for people who sign up with a referral code. The code tells Lium who sent you, "
         "and Lium pays the referrer a share of your top-ups (5% for 3 months, then 2.5% for 3 more). Your prices are the same either way."),
        ("Is there free credit for new accounts?",
         "Yes. Lium's grants page lists a $5 credit when you sign up with e-mail. It must be used on a GPU within 14 days. "
         "It's one per person, and it can run out for the day. Startups, researchers and open-source projects can also e-mail "
         "support@lium.io to ask for more credit."),
        ("Is there a Lium promo code or coupon?",
         "Lium has no public promo codes. The ways to save are the $5 signup credit, the 2.5% bonus when you top up with crypto, "
         "TAO or Bittensor alpha, and spot pods, which are cheaper but can be reclaimed by the provider."),
        ("How does Lium billing work?",
         "Per second, with no minimum and no reservation. Billing stops when you delete the pod or it reaches its scheduled end. "
         "Your balance must cover 15 minutes of the new pod plus 15 minutes of each pod already running."),
        ("How can I pay?",
         "Card, crypto (you pick the coin and network), TAO or Bittensor alpha. Crypto, TAO and alpha top-ups get a 2.5% bonus."),
        ("What is Lium?",
         "A GPU rental marketplace run by Datura AI Corp. Independent providers list GPU machines, Lium benchmarks them, and you rent "
         "them by the second through the website, a CLI (<code>pip install lium.io</code>), a Python SDK or an API."),
        ("Is this site run by Lium?",
         "No. It's an independent site that shares a referral code and a copy of Lium's public prices."),
    ]

    cards = []
    if cheapest:
        cards.append(f"<div class='card'><b>{usd(cheapest['min_price_usd_per_gpu_hour'])}/hr</b><span>cheapest GPU free now ({e(cheapest['name'])})</span></div>")
    if h100:
        cards.append(f"<div class='card'><b>{usd(h100['min_price_usd_per_gpu_hour'])}/hr</b><span>H100 80GB from</span></div>")
    if fleet:
        cards.append(f"<div class='card'><b>{fleet.get('listed_gpus', 0):,}</b><span>GPUs listed, {fleet.get('available_gpus', 0):,} free now</span></div>")
    cards.append("<div class='card'><b>$5</b><span>signup credit for new accounts</span></div>")

    body = f"""
<h1>Lium Referral Code ({year}): {e(CODE)}</h1>
<p class="lead">Use this code in the “Referral code” field when you sign up for Lium, the per-second GPU rental marketplace.
New accounts get a $5 signup credit to try a GPU.</p>
{codebox()}
<div class="grid">{''.join(cards)}</div>

<h2>How to use the code</h2>
<ol class="steps">
<li>Open the <a href="{e(SIGNUP)}" rel="nofollow sponsored">Lium signup page</a>.</li>
<li>Check that the “Referral code” field says <b>{e(CODE)}</b>. If it's empty, paste it in.</li>
<li>Sign up with e-mail. The $5 signup credit lands on your balance right away (while Lium's daily credit budget lasts).</li>
<li>Pick a GPU, start a pod and SSH in. Rent within 14 days or the credit expires.</li>
</ol>
<p>Or from a terminal:</p>
<div class="tablewrap" style="padding:12px 16px;background:var(--panel)"><code>pip install lium.io &amp;&amp; lium up --gpu H100 --ttl 1h</code></div>

<h2 id="prices">Lium GPU prices right now</h2>
{price_table(models, updated)}

<h2>Ways to save on Lium</h2>
<div class="grid">
<div class="card"><b>$5</b><span>free credit when you sign up with e-mail, use it within 14 days</span></div>
<div class="card"><b>+2.5%</b><span>bonus on crypto, TAO and Bittensor alpha top-ups</span></div>
<div class="card"><b>Spot</b><span>cheaper pods; the provider can reclaim them</span></div>
<div class="card"><b>Grants</b><span>startups, research and open source can e-mail support@lium.io for more credit</span></div>
</div>
<p><a href="/free-credits">How to get Lium free credits →</a></p>

<h2 id="faq">FAQ</h2>
{faq_html(faq)}
"""
    title = f"Lium Referral Code {year}: {CODE} (+$5 Signup Credit)"
    desc = (f"Lium referral code: {CODE}. Paste it in the “Referral code” field at signup; new accounts get $5 of GPU credit. "
            f"Live H100, H200, B200 and RTX 5090 prices.")
    site_ld = {"@context": "https://schema.org", "@type": "WebSite", "name": SITE_NAME, "alternateName": DOMAIN,
               "url": BASE + "/", "inLanguage": "en"}
    return page("index.html", title, desc, body, [site_ld, faq_ld(faq)],
                og="/og/home.png", og_alt=f"Lium referral code {CODE}")


def build_gpu(m, models, updated):
    name = m["name"]
    lo = m["min_price_usd_per_gpu_hour"]
    avail = m["available_gpus"]
    arch = ARCH.get((m.get("architecture") or "").lower(), (m.get("architecture") or "").title())
    cls = CLASS.get(m.get("gpu_class"), m.get("gpu_class") or "")
    peers = [p for p in models if p["gpu_class"] == m["gpu_class"] and p["slug"] != m["slug"]][:8]
    status = (f"{avail} GPU{'s' if avail != 1 else ''} free on {m['available_nodes']} pod{'s' if m['available_nodes'] != 1 else ''}"
              if avail else "none free right now")
    day = lo * 24
    month = lo * 24 * 30

    faq = [
        (f"How much does a {name} cost on Lium?",
         f"From {usd(lo)} per GPU-hour ({price_range(m)} across current listings), billed per second. "
         f"That's about {usd(day)} a day or {usd(month)} for 30 days at the lowest price."),
        (f"Is the {name} available on Lium now?",
         f"At the last update: {status}. {m['listed_gpus']} are listed in total and {m['rented_gpus']} are rented."),
        ("Is there a discount code?",
         f"There are no public promo codes. New accounts get $5 of signup credit; use referral code {e(CODE)} when you sign up."),
    ]

    peer_rows = price_table(peers, updated) if peers else ""
    body = f"""
<div class="crumbs"><a href="/">Lium referral code</a> › <a href="/#prices">GPU prices</a> › {e(name)}</div>
<h1>Lium {e(name)} price: from {usd(lo)}/hour</h1>
<p class="lead">Rent an NVIDIA {e(name)} ({m['vram_gb']} GB) on Lium, billed per second. Right now: {e(status)}.</p>
<div class="grid">
<div class="card"><b>{price_range(m)}</b><span>per GPU-hour</span></div>
<div class="card"><b>{m['vram_gb']} GB</b><span>VRAM{(' · ' + e(arch)) if arch else ''}</span></div>
<div class="card"><b>{avail}</b><span>free now, {m['listed_gpus']} listed</span></div>
<div class="card"><b>{usd(month)}</b><span>30 days at the lowest price</span></div>
</div>
{codebox("Sign up with our referral code to rent it")}
<p><a href="{e(m['url'])}" rel="nofollow">See live {e(name)} listings on lium.io</a>
· <a href="{e(m['browse_url'])}" rel="nofollow">Browse pods</a></p>
<h2>{e(name)} on Lium: FAQ</h2>
{faq_html(faq)}
{f'<h2>Other {e(cls.lower())} GPUs</h2>' + peer_rows if peers else ''}
<p class="small">Prices updated {e(updated)}.</p>
"""
    title = f"Lium {name} Price: from {usd(lo)}/hr"
    desc = (f"Rent an NVIDIA {name} on Lium from {usd(lo)}/hr, billed per second. "
            f"{m['vram_gb']} GB VRAM, live availability, and referral code {CODE}.")
    return page(f"gpu/{m['slug']}.html", title, desc, body, [faq_ld(faq)],
                og=f"/og/gpu/{m['slug']}.png", og_alt=f"Lium {name}: from {usd(lo)} per GPU-hour",
                crumbs=[(SITE_NAME, BASE + "/"), ("GPU prices", BASE + "/#prices"), (name, canonical(f"gpu/{m['slug']}.html"))])


FAVICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#7c5cff"/>
<path d="M22 16v32h22" fill="none" stroke="#fff" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/></svg>"""


def build_free_credits(models, year):
    cheap = [m for m in models if m["available_gpus"] > 0]
    cheap.sort(key=lambda m: m["min_price_usd_per_gpu_hour"])
    rows = "".join(f"<tr><td><a href='/gpu/{e(m['slug'])}'>{e(m['name'])}</a></td><td class='num'>{usd(m['min_price_usd_per_gpu_hour'])}</td>"
                   f"<td class='num'>{5 / m['min_price_usd_per_gpu_hour']:.1f} h</td></tr>" for m in cheap[:10])
    faq = [
        ("How much free credit does Lium give?",
         "$5 when you sign up with e-mail. It lands on your balance straight away and must be used on a GPU within 14 days."),
        ("Why didn't I get the $5 credit?",
         "Lium gives one credit per person. Signups that look automated, or that come after the day's credit budget is spent, get no credit. "
         "The credit is also skipped if an account has already signed up from the same IP address."),
        ("Can I get more than $5?",
         "Startups, researchers and open-source projects can ask. Sign up, then e-mail support@lium.io from that account with what you're "
         "building, a link, and the GPU model and hours you need. There's no fixed amount, and granted credit expires within 90 days."),
        ("Does the referral code add extra credit?",
         f"No. The $5 is the same with or without a code. Using {e(CODE)} supports this site at no cost to you."),
    ]
    body = f"""
<div class="crumbs"><a href="/">Lium referral code</a> › Free credits</div>
<h1>Lium free credits ({year}): how to get $5 of GPU time</h1>
<p class="lead">Every new Lium account gets a $5 signup credit. Here's how to claim it, what it buys, and how to ask for more.</p>
{codebox("Sign up with our referral code")}
<h2>How to claim the $5 signup credit</h2>
<ol class="steps">
<li>Open the <a href="{e(SIGNUP)}" rel="nofollow sponsored">Lium signup page</a> and sign up with e-mail.</li>
<li>The $5 lands on your balance right away (one per person, while the day's credit budget lasts).</li>
<li>Rent a GPU within 14 days. After that the credit expires.</li>
</ol>
<h2>What $5 buys right now</h2>
<p>Lium bills per second, so $5 goes further than it sounds. Cheapest GPUs free right now:</p>
<div class="tablewrap"><table><thead><tr><th>GPU</th><th class="num">From $/hr</th><th class="num">$5 lasts</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<h2>More credit for startups, research and open source</h2>
<p>Lium's grants program has no fixed amount. After signing up, e-mail <b>support@lium.io</b> from your account with what you're
building, a link to it, and the GPU model and hours you need. Lium replies by e-mail, and any credit it grants lands on your balance
and expires within 90 days.</p>
<h2>Other ways to save</h2>
<ul>
<li>Top up with crypto, TAO or Bittensor alpha for a 2.5% bonus.</li>
<li>Rent spot pods. They're cheaper, but the provider can reclaim them.</li>
<li>Set a scheduled end time (<code>--ttl</code>) so a forgotten pod doesn't keep billing.</li>
</ul>
<h2>FAQ</h2>
{faq_html(faq)}
<p class="small">Source: lium.io/grants. Terms can change; check Lium's site before relying on them.</p>
"""
    return page("free-credits.html", f"Lium Free Credits {year}: Get $5 of GPU Time (+ Grants)",
                "How to get Lium free credits: $5 signup credit for new accounts, what it buys, and how startups and researchers can ask for more.",
                body, [faq_ld(faq)], og="/og/free-credits.png", og_alt="Lium free credits: $5 of GPU time",
                crumbs=[(SITE_NAME, BASE + "/"), ("Free credits", canonical("free-credits.html"))])


def main():
    data, live = load_pricing()
    gen = data.get("generated_at") or ""
    try:
        t = dt.datetime.fromisoformat(gen.replace("Z", "+00:00"))
    except ValueError:
        t = dt.datetime.now(dt.timezone.utc)
    updated = t.strftime("%-d %b %Y, %H:%M UTC")
    year = t.year

    # Only models that actually have listings; cheapest-available first, then sold-out by price.
    models = [m for m in data["models"] if m.get("listed_gpus", 0) > 0 and m.get("slug")]
    models.sort(key=lambda m: (m["available_gpus"] == 0, -m["min_price_usd_per_gpu_hour"]))

    if os.path.exists(DIST):
        shutil.rmtree(DIST)
    os.makedirs(os.path.join(DIST, "gpu"))
    STATE["modified"] = t.isoformat()

    try:
        import og
        os.makedirs(os.path.join(DIST, "og", "gpu"))
        fleet = data.get("fleet", {})
        avail = [m for m in models if m["available_gpus"] > 0]
        stats = None
        if avail:
            c = min(avail, key=lambda m: m["min_price_usd_per_gpu_hour"])
            stats = (f"GPUs from {usd(c['min_price_usd_per_gpu_hour'])}/hr", f"{fleet.get('available_gpus', 0):,} GPUs free now")
        og.home(os.path.join(DIST, "og", "home.png"), CODE, stats)
        og.credits(os.path.join(DIST, "og", "free-credits.png"), CODE)
        for m in models:
            sub = (f"{m['available_gpus']} free now" if m["available_gpus"] else "sold out right now")
            og.gpu(os.path.join(DIST, "og", "gpu", m["slug"] + ".png"), CODE, m["name"],
                   usd(m["min_price_usd_per_gpu_hour"]), sub, m["vram_gb"])
        og.icons(DIST)
        STATE["images"] = True
    except ImportError as ex:
        print(f"Pillow not available ({ex}); building without share images", file=sys.stderr)

    def write(rel, text):
        with open(os.path.join(DIST, rel), "w") as f:
            f.write(text)

    write("index.html", build_index(data, models, updated, year))
    for m in models:
        write(f"gpu/{m['slug']}.html", build_gpu(m, models, updated))
    write("free-credits.html", build_free_credits(models, year))

    write("404.html", page("404.html", "Page not found | Lium Referral Code", "Page not found.",
                           f"<h1>Page not found</h1><p>Looking for the Lium referral code? It's <b>{e(CODE)}</b>.</p>{codebox()}",
                           noindex=True))
    write("site.webmanifest", json.dumps({"name": SITE_NAME, "short_name": "liumcode", "start_url": "/", "display": "browser",
                                          "background_color": "#0b0d12", "theme_color": "#0b0d12",
                                          "icons": [{"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
                                                    {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"}]}))
    write(f"{INDEXNOW_KEY}.txt", INDEXNOW_KEY)
    write("favicon.svg", FAVICON)
    write("CNAME", DOMAIN + "\n")
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")

    lastmod = t.strftime("%Y-%m-%d")
    urls = [BASE + "/", BASE + "/free-credits"] + [f"{BASE}/gpu/{m['slug']}" for m in models]
    write("urls.txt", "\n".join(urls) + "\n")  # for the IndexNow ping in CI
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + "".join(f"<url><loc>{u}</loc><lastmod>{lastmod}</lastmod></url>\n" for u in urls) + "</urlset>\n")

    lines = [f"# Lium referral code: {CODE}", "",
             f"> Unofficial site. Lium (lium.io) is a per-second GPU rental marketplace. Sign up at {SIGNUP} "
             f"or enter {CODE} in the 'Referral code' field. New accounts get a $5 signup credit.", "",
             f"## GPU prices (USD per GPU-hour, {updated})", ""]
    lines += [f"- [{m['name']}]({BASE}/gpu/{m['slug']}): {price_range(m)}, {m['vram_gb']} GB, {m['available_gpus']} free"
              for m in models]
    lines += ["", "## Guides", "", f"- [Lium free credits]({BASE}/free-credits): $5 signup credit and grants"]
    write("llms.txt", "\n".join(lines) + "\n")

    print(f"built {len(models) + 1} pages into dist/ ({'live' if live else 'fallback'} prices, {updated})", file=sys.stderr)


if __name__ == "__main__":
    main()
