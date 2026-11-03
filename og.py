"""Social share images (1200x630) and PNG icons. Needs Pillow; build.py skips images without it."""
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(ROOT, "fonts", "Inter.ttf")

BG = (11, 13, 18)
PANEL = (24, 28, 38)
LINE = (52, 58, 76)
TEXT = (236, 238, 244)
MUTED = (154, 161, 178)
ACCENT = (124, 92, 255)
ACCENT2 = (164, 139, 255)
OK = (62, 207, 142)

W, H = 1200, 630


def font(size, weight="Bold"):
    f = ImageFont.truetype(FONT, size)
    f.set_variation_by_name(weight)
    return f


def fit(draw, text, max_w, size, weight="Bold", min_size=36):
    while size > min_size:
        f = font(size, weight)
        if draw.textlength(text, font=f) <= max_w:
            return f
        size -= 4
    return font(min_size, weight)


def logo(size):
    """Rounded purple square with an L, same as favicon.svg."""
    s = size * 4
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, s - 1, s - 1], radius=int(s * 14 / 64), fill=ACCENT)
    k = s / 64
    w = int(7 * k)
    d.line([(22 * k, 16 * k), (22 * k, 48 * k), (44 * k, 48 * k)], fill="white", width=w, joint="curve")
    for x, y in ((22 * k, 16 * k), (22 * k, 48 * k), (44 * k, 48 * k)):
        d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill="white")
    return im.resize((size, size), Image.LANCZOS)


def base():
    im = Image.new("RGB", (W, H), BG)
    glow = Image.new("RGB", (W, H), BG)
    g = ImageDraw.Draw(glow)
    g.ellipse([700, -260, 1500, 420], fill=(58, 40, 140))
    g.ellipse([-300, 380, 400, 900], fill=(30, 26, 70))
    glow = glow.filter(ImageFilter.GaussianBlur(140))
    im = Image.blend(im, glow, 0.9)
    d = ImageDraw.Draw(im)
    # subtle grid
    for x in range(0, W, 60):
        d.line([(x, 0), (x, H)], fill=(18, 21, 29))
    for y in range(0, H, 60):
        d.line([(0, y), (W, y)], fill=(18, 21, 29))
    lg = logo(56)
    im.paste(lg, (64, 56), lg)
    d.text((136, 84), "liumcode.com", font=font(30, "SemiBold"), fill=TEXT, anchor="lm")
    return im, d


def code_pill(im, d, code, y, label="Referral code"):
    f_label = font(24, "Medium")
    f_code = font(46, "Bold")
    tw = d.textlength(code, font=f_code)
    x0, x1 = 64, 64 + 48 + tw
    d.text((64, y - 16), label.upper(), font=f_label, fill=MUTED, anchor="ls")
    d.rounded_rectangle([x0, y, x1, y + 84], radius=16, fill=PANEL, outline=ACCENT, width=3)
    d.text((x0 + 24, y + 42), code, font=f_code, fill=TEXT, anchor="lm")
    return x1


def home(path, code, stats):
    im, d = base()
    d.text((64, 230), "Lium Referral Code", font=font(84, "ExtraBold"), fill=TEXT, anchor="ls")
    d.text((64, 292), "Per-second GPU rental · $5 signup credit", font=font(36, "Medium"), fill=MUTED, anchor="ls")
    x1 = code_pill(im, d, code, 380)
    if stats:
        f = font(30, "SemiBold")
        y = 422
        d.text((x1 + 40, y - 22), stats[0], font=f, fill=OK, anchor="lm")
        d.text((x1 + 40, y + 22), stats[1], font=f, fill=MUTED, anchor="lm")
    d.text((64, 560), "H100 · H200 · B200 · RTX 5090 · RTX 4090 · A100 · L40S", font=font(28, "Medium"), fill=ACCENT2, anchor="ls")
    im.save(path, optimize=True)


def gpu(path, code, name, price, sub, vram):
    im, d = base()
    d.text((64, 196), "Rent on Lium", font=font(32, "SemiBold"), fill=ACCENT2, anchor="ls")
    d.text((64, 290), name, font=fit(d, name, W - 128, 88, "ExtraBold"), fill=TEXT, anchor="ls")
    f_price = font(64, "Bold")
    d.text((64, 380), f"from {price}", font=f_price, fill=TEXT, anchor="ls")
    pw = d.textlength(f"from {price}", font=f_price)
    d.text((64 + pw + 12, 380), "/ GPU-hour", font=font(34, "Medium"), fill=MUTED, anchor="ls")
    d.text((64, 432), f"{vram} GB VRAM · {sub}", font=font(30, "Medium"), fill=MUTED, anchor="ls")
    code_pill(im, d, code, 500)
    im.save(path, optimize=True)


def icons(dist):
    for size, name in ((180, "apple-touch-icon.png"), (192, "icon-192.png"), (512, "icon-512.png"), (48, "favicon-48.png")):
        bg = logo(size)
        if name == "apple-touch-icon.png":  # iOS draws its own rounded mask; fill the corners
            sq = Image.new("RGBA", (size, size), ACCENT + (255,))
            sq.alpha_composite(bg)
            bg = sq
        bg.save(os.path.join(dist, name), optimize=True)
    logo(48).save(os.path.join(dist, "favicon.ico"), sizes=[(16, 16), (32, 32), (48, 48)])


def credits(path, code):
    im, d = base()
    d.text((64, 230), "Lium Free Credits", font=font(84, "ExtraBold"), fill=TEXT, anchor="ls")
    d.text((64, 292), "$5 of GPU time for new accounts · grants for builders", font=font(34, "Medium"), fill=MUTED, anchor="ls")
    x1 = code_pill(im, d, code, 380)
    d.text((x1 + 40, 422), "$5", font=font(96, "ExtraBold"), fill=OK, anchor="lm")
    im.save(path, optimize=True)
