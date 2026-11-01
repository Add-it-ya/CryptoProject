"""Group 18 custom "cipher-cloud" theme: generates the slide backgrounds, icons and figures used by
build_deck.py. Everything is drawn procedurally (no stock template)."""
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = sys.argv[1] if len(sys.argv) > 1 else "assets"
os.makedirs(OUT, exist_ok=True)
W, H = 1920, 1080
random.seed(18)
np.random.seed(18)

NAVY0 = (5, 10, 24)
NAVY1 = (10, 24, 48)
CYAN = (34, 211, 238)
TEAL = (20, 184, 166)
VIOLET = (167, 139, 250)
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def gradient(w, h, c0, c1, angle=0.35):
    y, x = np.mgrid[0:h, 0:w]
    t = (x / w) * math.cos(angle) + (y / h) * math.sin(angle)
    t = (t - t.min()) / (t.max() - t.min())
    arr = np.zeros((h, w, 3), np.float32)
    for i in range(3):
        arr[..., i] = c0[i] * (1 - t) + c1[i] * t
    return arr


def glow(arr, cx, cy, r, color, strength):
    h, w, _ = arr.shape
    y, x = np.mgrid[0:h, 0:w]
    d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / r
    g = np.exp(-(d**2)) * strength
    for i in range(3):
        arr[..., i] = arr[..., i] * (1 - g) + color[i] * g
    return arr


def hex_grid(draw, w, h, size, color, alpha, region=None):
    dx = size * 1.5
    dy = size * math.sqrt(3)
    cols = int(w / dx) + 2
    rows = int(h / dy) + 2
    for c in range(cols):
        for r in range(rows):
            cx = c * dx
            cy = r * dy + (dy / 2 if c % 2 else 0)
            if region and not region(cx, cy):
                continue
            pts = [(cx + size * math.cos(math.radians(60 * k)), cy + size * math.sin(math.radians(60 * k))) for k in range(6)]
            a = alpha
            if callable(alpha):
                a = alpha(cx, cy)
            if a <= 0:
                continue
            draw.polygon(pts, outline=color + (int(a),))


def hex_rain(draw, x0, x1, h, alpha_fn, size=15):
    f = ImageFont.truetype(MONO, size)
    col_w = int(size * 1.9)
    for x in range(x0, x1, col_w):
        y = random.randint(-200, 0)
        while y < h:
            s = "%02x" % random.randint(0, 255)
            a = alpha_fn(x, y)
            if a > 0:
                draw.text((x, y), s, font=f, fill=CYAN + (int(a),))
            y += int(size * 1.35)


def network(draw, cx, cy, rx, ry, n, color, alpha_node, alpha_line, seed=1):
    rnd = random.Random(seed)
    pts = []
    for _ in range(n):
        # points distributed inside a cloud-like union of ellipses
        while True:
            x = rnd.uniform(-1, 1)
            y = rnd.uniform(-1, 1)
            inside = ((x + 0.45) ** 2 / 0.30 + (y - 0.15) ** 2 / 0.35 < 1) or ((x) ** 2 / 0.42 + (y + 0.15) ** 2 / 0.55 < 1) or (
                (x - 0.5) ** 2 / 0.28 + (y - 0.1) ** 2 / 0.38 < 1
            )
            if inside and y < 0.62:
                break
        pts.append((cx + x * rx, cy + y * ry))
    for i, p in enumerate(pts):
        d = sorted(range(n), key=lambda j: (pts[j][0] - p[0]) ** 2 + (pts[j][1] - p[1]) ** 2)
        for j in d[1:4]:
            draw.line([p, pts[j]], fill=color + (alpha_line,), width=1)
    for p in pts:
        r = rnd.choice([2, 2, 3, 4])
        draw.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=color + (alpha_node,))
    return pts


def to_img(arr):
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").convert("RGBA")


# --------------------------------------------------------------------------- content background
def content_bg():
    arr = gradient(W, H, NAVY0, NAVY1)
    arr = glow(arr, W * 0.95, -60, 620, (14, 70, 110), 0.55)
    arr = glow(arr, -100, H * 1.05, 520, (12, 40, 80), 0.45)
    img = to_img(arr)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    hex_grid(d, W, H, 34, CYAN, lambda x, y: max(0, 22 - 22 * (((x - W) ** 2 + (y) ** 2) ** 0.5) / 900))
    hex_rain(d, W - 150, W, H, lambda x, y: max(0, 70 - 70 * y / 700), 13)
    img = Image.alpha_composite(img, lay)
    # thin accent line under the title zone
    d = ImageDraw.Draw(img)
    for i in range(0, 260):
        a = int(220 * (1 - i / 260))
        d.line([(86 + i, 168), (87 + i, 168)], fill=CYAN + (a,), width=3)
    # footer rule
    d.line([(86, 1016), (W - 86, 1016)], fill=(40, 60, 95, 255), width=1)
    img.convert("RGB").save(os.path.join(OUT, "content_bg.png"), optimize=True)


# --------------------------------------------------------------------------- title background
def padlock(size, body=(250, 204, 21), shackle=(250, 204, 21), hole=(8, 16, 34)):
    S = size * 4
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    bw, bh = int(S * 0.62), int(S * 0.46)
    bx, by = (S - bw) // 2, int(S * 0.46)
    t = int(S * 0.085)
    sw = int(S * 0.40)
    sx = (S - sw) // 2
    d.arc([sx, int(S * 0.12), sx + sw, int(S * 0.12) + sw], 180, 360, fill=shackle, width=t)
    d.line([(sx + t // 2, int(S * 0.12) + sw // 2), (sx + t // 2, by + 4)], fill=shackle, width=t)
    d.line([(sx + sw - t // 2, int(S * 0.12) + sw // 2), (sx + sw - t // 2, by + 4)], fill=shackle, width=t)
    d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=int(S * 0.07), fill=body)
    r = int(S * 0.06)
    cx, cy = S // 2, by + int(bh * 0.42)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=hole)
    d.rectangle([cx - r // 2, cy, cx + r // 2, cy + int(bh * 0.32)], fill=hole)
    return im.resize((size, size), Image.LANCZOS)


def title_bg():
    arr = gradient(W, H, (4, 8, 20), (9, 26, 52), 0.2)
    arr = glow(arr, W * 0.74, H * 0.45, 560, (10, 80, 120), 0.6)
    arr = glow(arr, W * 0.2, H * 1.1, 600, (20, 30, 80), 0.35)
    img = to_img(arr)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    hex_grid(d, W, H, 40, CYAN, lambda x, y: max(0, 26 - 26 * (((x - W * 0.74) ** 2 + (y - H * 0.45) ** 2) ** 0.5) / 760))
    hex_rain(d, W - 420, W, H, lambda x, y: max(0, 60 - 60 * abs(y - H / 2) / 620) * (0.3 + 0.7 * (x - (W - 420)) / 420), 14)
    img = Image.alpha_composite(img, lay)
    # network-cloud
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    network(d, W * 0.74, H * 0.47, 400, 300, 120, CYAN, 230, 70, seed=4)
    blur = lay.filter(ImageFilter.GaussianBlur(6))
    img = Image.alpha_composite(img, blur)
    img = Image.alpha_composite(img, lay)
    # padlock with glow
    lk = padlock(250)
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g.alpha_composite(lk, (int(W * 0.74 - 125), int(H * 0.47 - 120)))
    gl = g.filter(ImageFilter.GaussianBlur(28))
    img = Image.alpha_composite(img, gl)
    img = Image.alpha_composite(img, g)
    # left fade so the title text stays readable
    y, x = np.mgrid[0:H, 0:W]
    fade = np.clip(1 - (x - W * 0.33) / (W * 0.25), 0, 1) * 0.82
    ov = np.zeros((H, W, 4), np.uint8)
    ov[..., 0], ov[..., 1], ov[..., 2] = 5, 10, 24
    ov[..., 3] = (fade * 255).astype(np.uint8)
    img = Image.alpha_composite(img, Image.fromarray(ov, "RGBA"))
    img.convert("RGB").save(os.path.join(OUT, "title_bg.png"), optimize=True)


# --------------------------------------------------------------------------- icons
def icon_canvas(S=512):
    return Image.new("RGBA", (S, S), (0, 0, 0, 0))


def save_icon(im, name, size=256):
    im.resize((size, size), Image.LANCZOS).save(os.path.join(OUT, f"ic_{name}.png"))


def ic_cloud(color):
    im = icon_canvas()
    d = ImageDraw.Draw(im)
    d.ellipse([60, 200, 250, 390], fill=color)
    d.ellipse([150, 110, 360, 320], fill=color)
    d.ellipse([280, 190, 460, 370], fill=color)
    d.rounded_rectangle([110, 280, 410, 390], radius=50, fill=color)
    return im


def ic_user(color):
    im = icon_canvas()
    d = ImageDraw.Draw(im)
    d.ellipse([176, 70, 336, 230], fill=color)
    d.pieslice([96, 250, 416, 570], 180, 360, fill=color)
    return im


def ic_attacker(color):
    im = icon_canvas()
    d = ImageDraw.Draw(im)
    d.pieslice([96, 250, 416, 570], 180, 360, fill=color)
    d.ellipse([160, 60, 352, 252], fill=color)  # hood
    d.rounded_rectangle([196, 130, 316, 205], radius=20, fill=(8, 16, 34))  # face shadow
    d.rectangle([215, 155, 245, 170], fill=color)
    d.rectangle([267, 155, 297, 170], fill=color)
    return im


def ic_key(color):
    im = icon_canvas()
    d = ImageDraw.Draw(im)
    d.ellipse([60, 160, 250, 350], outline=color, width=48)
    d.rectangle([230, 230, 460, 280], fill=color)
    d.rectangle([380, 280, 420, 350], fill=color)
    d.rectangle([310, 280, 345, 330], fill=color)
    return im


def ic_file(color):
    im = icon_canvas()
    d = ImageDraw.Draw(im)
    d.polygon([(120, 50), (320, 50), (400, 130), (400, 460), (120, 460)], fill=color)
    d.polygon([(320, 50), (320, 130), (400, 130)], fill=(255, 255, 255, 120))
    for i, y in enumerate([200, 260, 320, 380]):
        d.rectangle([165, y, 355 - (60 if i == 3 else 0), y + 22], fill=(8, 16, 34, 200))
    return im


def ic_shield(color, mark=(8, 16, 34)):
    im = icon_canvas()
    d = ImageDraw.Draw(im)
    d.polygon([(256, 40), (440, 110), (420, 300), (256, 470), (92, 300), (72, 110)], fill=color)
    d.line([(170, 260), (235, 330), (350, 190)], fill=mark, width=46, joint="curve")
    return im


def ic_warning(color):
    im = icon_canvas()
    d = ImageDraw.Draw(im)
    d.polygon([(256, 50), (470, 440), (42, 440)], fill=color)
    d.rectangle([236, 170, 276, 330], fill=(8, 16, 34))
    d.ellipse([234, 360, 278, 404], fill=(8, 16, 34))
    return im


def ic_db(color):
    im = icon_canvas()
    d = ImageDraw.Draw(im)
    for y in [330, 230, 130]:
        d.rounded_rectangle([110, y, 402, y + 120], radius=30, fill=color)
        d.ellipse([110, y - 40, 402, y + 40], fill=color)
        d.arc([110, y - 40, 402, y + 40], 0, 180, fill=(8, 16, 34), width=10)
    d.ellipse([110, 90, 402, 170], fill=color)
    return im


def ic_lock(color):
    return padlock(512, body=color, shackle=color)


def ic_sign(color):
    im = icon_canvas()
    d = ImageDraw.Draw(im)
    d.polygon([(120, 50), (320, 50), (400, 130), (400, 460), (120, 460)], fill=color)
    d.line([(160, 390), (200, 340), (230, 380), (270, 320), (300, 370), (360, 350)], fill=(8, 16, 34), width=18, joint="curve")
    d.ellipse([280, 150, 380, 250], outline=(8, 16, 34), width=16)
    return im


def icons():
    C = CYAN + (255,)
    R = (248, 113, 113, 255)
    G = (52, 211, 153, 255)
    A = (251, 191, 36, 255)
    V = VIOLET + (255,)
    save_icon(ic_cloud(V), "cloud")
    save_icon(ic_user(C), "user")
    save_icon(ic_user(G), "user_green")
    save_icon(ic_attacker(R), "attacker")
    save_icon(ic_key(A), "key")
    save_icon(ic_key(G), "key_green")
    save_icon(ic_key(R), "key_red")
    save_icon(ic_file(C), "file")
    save_icon(ic_shield(G), "shield")
    save_icon(ic_warning(R), "warning")
    save_icon(ic_warning(A), "warning_amber")
    save_icon(ic_db(V), "db")
    save_icon(ic_lock(A), "lock")
    save_icon(ic_lock(G), "lock_green")
    save_icon(ic_sign(G), "sign")


# --------------------------------------------------------------------------- elliptic curve figure
def curve_fig():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    a, b = -2.0, 2.4
    fig, ax = plt.subplots(figsize=(4.2, 3.2), dpi=220)
    fig.patch.set_alpha(0)
    ax.set_facecolor("none")
    y, x = np.ogrid[-4:4:800j, -2.5:3.2:800j]
    ax.contour(x.ravel(), y.ravel(), y**2 - x**3 - a * x - b, [0], colors=["#22d3ee"], linewidths=2.4)
    # P, Q and P+Q
    def yv(x0, s=1):
        return s * math.sqrt(x0**3 + a * x0 + b)

    P = (-1.6, yv(-1.6))
    Q = (0.4, yv(0.4))
    m = (Q[1] - P[1]) / (Q[0] - P[0])
    x3 = m * m - P[0] - Q[0]
    y3 = m * (P[0] - x3) - P[1]
    xs = np.linspace(-2.2, x3 + 0.3, 10)
    ax.plot(xs, P[1] + m * (xs - P[0]), color="#fbbf24", lw=1.4, ls="--")
    ax.plot([x3, x3], [-y3, y3], color="#a78bfa", lw=1.2, ls=":")
    for (px, py), lab, col in [(P, "P", "#fbbf24"), (Q, "Q", "#fbbf24"), ((x3, y3), "P+Q", "#34d399")]:
        ax.plot(px, py, "o", color=col, ms=7)
        ax.annotate(lab, (px, py), textcoords="offset points", xytext=(6, 6), color=col, fontsize=12, fontweight="bold")
    ax.axhline(0, color="#334155", lw=0.8)
    ax.axvline(0, color="#334155", lw=0.8)
    ax.set_xlim(-2.5, 3.2)
    ax.set_ylim(-4, 4)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.text(-2.4, 3.45, "y² = x³ + ax + b", color="#e2e8f0", fontsize=12, family="DejaVu Sans Mono")
    plt.tight_layout(pad=0.1)
    fig.savefig(os.path.join(OUT, "ecc_curve.png"), transparent=True)
    plt.close(fig)


# --------------------------------------------------------------------------- ECB strip from bench output
def ecb_strip(bench_dir):
    ims = []
    for n in ["ecb_original", "ecb_base_encrypted", "ecb_proposed_encrypted"]:
        p = os.path.join(bench_dir, n + ".bmp")
        im = Image.open(p).convert("RGB")
        ims.append(im)
        im.save(os.path.join(OUT, n + ".png"))


if __name__ == "__main__":
    content_bg()
    title_bg()
    icons()
    curve_fig()
    if len(sys.argv) > 2:
        ecb_strip(sys.argv[2])
    print("assets written to", OUT)
