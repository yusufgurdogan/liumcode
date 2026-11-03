"""Price history storage and server-rendered SVG charts (no JS library; small hover script)."""
import csv
import datetime as dt
import html
import json
import os

FIELDS = ["ts", "slug", "min", "max", "ref", "available", "listed", "rented"]
GAP = dt.timedelta(hours=18)  # break the line when snapshots are missing for longer than this


def parse_ts(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def load(path):
    hist = {}
    if not os.path.exists(path):
        return hist
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            hist.setdefault(r["slug"], []).append({
                "t": parse_ts(r["ts"]), "min": float(r["min"]), "max": float(r["max"]),
                "available": int(r["available"]), "listed": int(r["listed"])})
    for v in hist.values():
        v.sort(key=lambda p: p["t"])
    return hist


def append(path, data):
    """Append one snapshot of the feed. Returns False if this snapshot is already recorded."""
    ts = data.get("generated_at")
    if not ts:
        return False
    last = None
    if os.path.exists(path):
        with open(path, newline="") as f:
            for r in csv.DictReader(f):
                last = r["ts"]
    if last and parse_ts(last) >= parse_ts(ts):
        return False
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(FIELDS)
        for m in data["models"]:
            if m.get("listed_gpus", 0) > 0 and m.get("slug"):
                w.writerow([ts, m["slug"], m["min_price_usd_per_gpu_hour"], m["max_price_usd_per_gpu_hour"],
                            m["reference_price_usd_per_gpu_hour"], m["available_gpus"], m["listed_gpus"], m["rented_gpus"]])
    return True


# ---------------------------------------------------------------- rendering

def _nice_step(span, target=4):
    raw = span / target if span > 0 else 1
    for m in (0.01, 0.02, 0.025, 0.05, 0.1, 0.2, 0.25, 0.5, 1, 2, 2.5, 5, 10, 20, 25, 50, 100, 200, 500):
        if m >= raw:
            return m
    return raw


def _ticks(lo, hi, zero=False):
    if zero:
        lo = 0
    if hi - lo < 1e-9:
        pad = max(abs(hi) * 0.1, 0.05)
        lo, hi = max(0, lo - pad), hi + pad
    step = _nice_step(hi - lo)
    start = int(lo / step) * step
    if start > lo:
        start -= step
    ticks, v = [], start
    while v < hi + step * 0.999:
        ticks.append(round(v, 6))
        v += step
    return ticks


def _segments(points):
    segs, cur = [], []
    for p in points:
        if cur and p["t"] - cur[-1]["t"] > GAP:
            segs.append(cur)
            cur = []
        cur.append(p)
    if cur:
        segs.append(cur)
    return segs


def _date_ticks(t0, t1, n=5):
    span = (t1 - t0).total_seconds()
    if span <= 0:
        return [t0]
    return [t0 + dt.timedelta(seconds=span * i / (n - 1)) for i in range(n)]


def _fmt_date(t, span_days):
    return t.strftime("%-d %b %H:%M") if span_days < 3 else t.strftime("%-d %b")


def line_chart(cid, points, key, label, fmt, band_key=None, zero=False, unit=""):
    """points: list of dicts with 't' and numeric keys. Renders an SVG line (+ optional min..max band)."""
    W, H, L, R, T, B = 720, 260, 56, 64, 16, 32
    pw, ph = W - L - R, H - T - B
    if not points:
        return ""
    vals = [p[key] for p in points] + ([p[band_key] for p in points] if band_key else [])
    ticks = _ticks(min(vals), max(vals), zero)
    y0, y1 = ticks[0], ticks[-1]
    t0, t1 = points[0]["t"], points[-1]["t"]
    span = (t1 - t0).total_seconds() or 1
    single = len(points) == 1

    def x(t):
        return L + (pw / 2 if single else (t - t0).total_seconds() / span * pw)

    def y(v):
        return T + ph - (v - y0) / (y1 - y0) * ph

    out = [f'<svg class="chart" id="{cid}" viewBox="0 0 {W} {H}" role="img" aria-label="{html.escape(label)}" preserveAspectRatio="none">']
    for tv in ticks:
        out.append(f'<line class="grid" x1="{L}" x2="{W - R}" y1="{y(tv):.1f}" y2="{y(tv):.1f}"/>')
        out.append(f'<text class="ax" x="{L - 8}" y="{y(tv):.1f}" text-anchor="end" dominant-baseline="middle">{html.escape(fmt(tv))}</text>')
    span_days = span / 86400
    if not single:
        dts = _date_ticks(t0, t1, 5 if span_days >= 1 else 3)
        for i, t in enumerate(dts):
            anchor = "start" if i == 0 else "end" if i == len(dts) - 1 else "middle"
            out.append(f'<text class="ax" x="{x(t):.1f}" y="{H - 10}" text-anchor="{anchor}">{_fmt_date(t, span_days)}</text>')
    else:
        out.append(f'<text class="ax" x="{x(t0):.1f}" y="{H - 10}" text-anchor="middle">{_fmt_date(t0, 0)}</text>')

    for seg in _segments(points):
        if band_key and len(seg) > 1:
            top = " ".join(f"{x(p['t']):.1f},{y(p[band_key]):.1f}" for p in seg)
            bot = " ".join(f"{x(p['t']):.1f},{y(p[key]):.1f}" for p in reversed(seg))
            out.append(f'<polygon class="band" points="{top} {bot}"/>')
        if len(seg) > 1:
            out.append('<polyline class="ln" points="' + " ".join(f"{x(p['t']):.1f},{y(p[key]):.1f}" for p in seg) + '"/>')
    last = points[-1]
    lx, ly = x(last["t"]), y(last[key])
    out.append(f'<circle class="dot" cx="{lx:.1f}" cy="{ly:.1f}" r="4.5"/>')
    out.append(f'<text class="lbl" x="{lx + 10:.1f}" y="{ly:.1f}" dominant-baseline="middle">{html.escape(fmt(last[key]))}</text>')
    # hover layer
    out.append(f'<line class="xh" x1="0" x2="0" y1="{T}" y2="{T + ph}" style="display:none"/>'
               f'<circle class="hd" r="5" style="display:none"/>'
               f'<rect class="hit" x="{L}" y="{T}" width="{pw}" height="{ph}"/>')
    out.append("</svg>")
    payload = [{"x": round(x(p["t"]), 1), "y": round(y(p[key]), 1), "d": p["t"].strftime("%-d %b %Y, %H:%M UTC"),
                "v": fmt(p[key]) + unit, "b": (fmt(p[band_key]) + unit) if band_key else None} for p in points]
    data = json.dumps(payload).replace("</", "<\\/")
    return (f'<div class="chartbox">{"".join(out)}<div class="tip" hidden></div>'
            f'<script type="application/json" class="cdata">{data}</script></div>')


def sparkline(points, key="min"):
    if len(points) < 2:
        return '<span class="small">–</span>'
    W, H = 80, 22
    vals = [p[key] for p in points]
    lo, hi = min(vals), max(vals)
    if hi - lo < 1e-9:
        lo, hi = lo - 1, hi + 1
    t0, t1 = points[0]["t"], points[-1]["t"]
    span = (t1 - t0).total_seconds() or 1
    pts = " ".join(f"{(p['t'] - t0).total_seconds() / span * (W - 4) + 2:.1f},{H - 3 - (p[key] - lo) / (hi - lo) * (H - 6):.1f}"
                   for p in points)
    first, lastv = vals[0], vals[-1]
    chg = (lastv - first) / first * 100 if first else 0
    word = "flat" if abs(chg) < 0.5 else (f"up {chg:.0f}%" if chg > 0 else f"down {-chg:.0f}%")
    return (f'<svg class="spark" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="7-day trend: {word}">'
            f'<polyline points="{pts}"/></svg> <span class="small">{word}</span>')


CHART_CSS = """
.chartbox{position:relative;background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:12px 8px 4px;margin:12px 0}
.chart{width:100%;height:auto;display:block;overflow:visible}
.chart .grid{stroke:var(--line);stroke-width:1}
.chart .ax{fill:var(--muted);font-size:12px;font-variant-numeric:tabular-nums}
.chart .ln{fill:none;stroke:var(--accent2);stroke-width:2;stroke-linejoin:round;stroke-linecap:round;vector-effect:non-scaling-stroke}
.chart .band{fill:var(--accent2);opacity:.16}
.chart .dot,.chart .hd{fill:var(--accent2);stroke:var(--panel);stroke-width:2}
.chart .lbl{fill:var(--text);font-size:13px;font-weight:600;font-variant-numeric:tabular-nums}
.chart .xh{stroke:var(--muted);stroke-width:1;stroke-dasharray:3 3}
.chart .hit{fill:transparent;cursor:crosshair}
.tip{position:absolute;pointer-events:none;background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:6px 10px;
font-size:13px;line-height:1.4;white-space:nowrap;box-shadow:0 4px 16px rgba(0,0,0,.25);transform:translate(-50%,-110%)}
.tip b{font-variant-numeric:tabular-nums}
.key{display:flex;gap:16px;flex-wrap:wrap;font-size:13px;color:var(--muted);margin:4px 0}
.key i{display:inline-block;width:14px;height:10px;border-radius:2px;margin-right:6px;vertical-align:middle}
.key .k-ln{height:2px;background:var(--accent2)}
.key .k-band{background:var(--accent2);opacity:.3}
.spark{vertical-align:middle}
.spark polyline{fill:none;stroke:var(--accent2);stroke-width:1.5;stroke-linejoin:round}
"""

CHART_JS = """
<script>
document.querySelectorAll('.chartbox').forEach(function(box){
var svg=box.querySelector('svg'),tip=box.querySelector('.tip'),pts=JSON.parse(box.querySelector('.cdata').textContent);
var xh=svg.querySelector('.xh'),hd=svg.querySelector('.hd'),hit=svg.querySelector('.hit');
function show(cx){var vb=svg.viewBox.baseVal,r=svg.getBoundingClientRect(),sx=(cx-r.left)*vb.width/r.width,b=pts[0],bd=1e9;
pts.forEach(function(p){var d=Math.abs(p.x-sx);if(d<bd){bd=d;b=p}});
xh.setAttribute('x1',b.x);xh.setAttribute('x2',b.x);xh.style.display='';hd.setAttribute('cx',b.x);hd.setAttribute('cy',b.y);hd.style.display='';
tip.innerHTML='<div class=\"small\">'+b.d+'</div><b>'+b.v+'</b>'+(b.b?' <span class=\"small\">up to '+b.b+'</span>':'');
tip.hidden=false;var br=box.getBoundingClientRect();tip.style.left=Math.min(Math.max(b.x*r.width/vb.width+(r.left-br.left),70),br.width-70)+'px';
tip.style.top=(b.y*r.height/vb.height+(r.top-br.top))+'px'}
function hide(){tip.hidden=true;xh.style.display='none';hd.style.display='none'}
hit.addEventListener('pointermove',function(e){show(e.clientX)});hit.addEventListener('pointerdown',function(e){show(e.clientX)});
hit.addEventListener('pointerleave',hide);
});
</script>
"""
