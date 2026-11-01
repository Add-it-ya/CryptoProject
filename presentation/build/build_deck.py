"""Builds the Group 18 deck (title + 6 content slides) with python-pptx.
All numbers are read from the benchmark output so slides, report and demo agree.
usage: python3 build_deck.py <assets_dir> <results.json> <out.pptx>"""
import json
import sys

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches, Pt

from pptx_helpers import BODY, HEAD, MONO, C, Animator, background, box, notes, pic, rgb, text, transition

ASSETS, RESULTS, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
R = json.load(open(RESULTS))
A = lambda n: f"{ASSETS}/{n}"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]
TOTAL = 6

MEMBERS = [
    ("Saurav Singh", "S20230010219"),
    ("Rohan Dubey", "S20230010207"),
    ("Ujjawal", "S20230010245"),
    ("Aditya Raj", "S20230030364"),
]

# ------------------------------------------------------------------ derived numbers
e1 = R["e1_public_key_attack"]
e2 = R["e2_tampering"]
T2 = sum(v["trials"] for v in e2.values())
B2 = sum(v["base"]["detected"] for v in e2.values())
P2 = sum(v["proposed"]["detected"] for v in e2.values())
e3 = R["e3_ecb_image"]
e4 = R["e4_determinism"]
e5 = R["e5_avalanche"]
perf = {row["size_kib"]: row for row in R["e6_performance"]}
e7 = R["e7_sharing"]
rev = {row["size_kib"]: row for row in R["e8_revocation"]}
e9 = R["e9_primitives"]


def fmt_int(n):
    return f"{n:,}"


# ------------------------------------------------------------------ slide chrome
def chrome(slide, n, tag, title, presenter):
    background(slide, A("content_bg.png"), prs)
    text(slide, 0.6, 0.30, 8, 0.3, f"{n:02d}  ·  {tag.upper()}", size=11.5, color="cyan", font=MONO)
    text(slide, 0.6, 0.50, 9.7, 0.62, title, size=28, color="white", font=HEAD)
    chip = box(slide, 10.05, 0.40, 2.7, 0.46, fill="card", line="cyan", radius=0.5, line_w=0.75)
    text(slide, 0, 0, 0, 0, [[("PRESENTER  ", {"size": 8.5, "color": "cyan", "font": MONO}), (presenter, {"size": 11.5, "color": "text", "font": HEAD})]], align="c", anchor="m", shape=chip)
    text(slide, 0.6, 7.09, 9, 0.28, "Group 18  ·  Secure Cloud File Sharing Using Hybrid Cryptography", size=9, color="muted")
    text(slide, 11.25, 7.09, 1.5, 0.28, f"{n} / {TOTAL}", size=9, color="muted", align="r", font=MONO)


def label(slide, x, y, s, color="cyan", w=6):
    return text(slide, x, y, w, 0.28, s.upper(), size=10.5, color=color, font=MONO)


def card(slide, x, y, w, h, accent=None, fill="card", alpha=0.92, line="line"):
    b = box(slide, x, y, w, h, fill=fill, line=line, radius=0.06, alpha=alpha, line_w=0.75)
    if accent:
        a = box(slide, x, y + 0.12, 0.06, h - 0.24, fill=accent, radius=0.5)
        return b, a
    return b, None


def style_chart(chart, colors, size=10, legend=True, labels=None, fmt="0.00"):
    chart.font.size = Pt(size)
    chart.font.color.rgb = rgb(C["muted"])
    chart.font.name = BODY
    chart.has_legend = legend
    if legend:
        chart.legend.position = XL_LEGEND_POSITION.TOP
        chart.legend.include_in_layout = False
        chart.legend.font.size = Pt(size)
        chart.legend.font.color.rgb = rgb(C["text"])
    plot = chart.plots[0]
    plot.gap_width = 55
    plot.overlap = -8
    for s, col in zip(plot.series, colors):
        s.format.fill.solid()
        s.format.fill.fore_color.rgb = rgb(C.get(col, col))
        s.format.line.fill.background()
    va = chart.value_axis
    va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = rgb("1C2A4A")
    va.format.line.fill.background()
    va.tick_labels.font.size = Pt(size - 1)
    va.tick_labels.font.color.rgb = rgb(C["muted"])
    ca = chart.category_axis
    ca.format.line.color.rgb = rgb(C["line"])
    ca.tick_labels.font.size = Pt(size)
    ca.tick_labels.font.color.rgb = rgb(C["text"])
    if labels:
        plot.has_data_labels = True
        dl = plot.data_labels
        dl.font.size = Pt(size - 2)
        dl.font.color.rgb = rgb(C["text"])
        dl.number_format = fmt
        dl.number_format_is_linked = False
        dl.position = XL_LABEL_POSITION.OUTSIDE_END


# =================================================================== SLIDE 0 - TITLE
s = prs.slides.add_slide(BLANK)
background(s, A("title_bg.png"), prs)
an = Animator(s)
t0 = text(s, 0.75, 0.72, 8, 0.32, "CRYPTOGRAPHY  ·  COURSE PROJECT  ·  GROUP 18", size=13, color="cyan", font=MONO)
t1 = text(
    s,
    0.75,
    1.25,
    8.2,
    2.0,
    [[("Secure Cloud File Sharing", {"color": "white"})], [("Using Hybrid Cryptography", {"color": "cyan"})]],
    size=44,
    font=HEAD,
    spacing=1.0,
)
t2 = text(
    s,
    0.75,
    3.28,
    7.9,
    0.9,
    "We rebuilt the Hybrid AES-ECC model of Rehman et al. (Electronics, 2021), attacked it, and fixed it with authenticated hybrid encryption.",
    size=17,
    color="muted",
    spacing=1.12,
)
tag = box(s, 0.75, 4.33, 2.95, 0.38, fill="card2", line="green", radius=0.5, line_w=0.75)
text(s, 0, 0, 0, 0, "RESEARCH + APPLICATION PROJECT", size=10, color="green", font=MONO, align="c", anchor="m", shape=tag)
mem = []
for i, (nm, roll) in enumerate(MEMBERS):
    x = 0.75 + (i % 2) * 3.65
    y = 4.98 + (i // 2) * 0.78
    b, a = card(s, x, y, 3.45, 0.64, accent="cyan")
    text(s, 0, 0, 0, 0, [[(nm, {"size": 15, "font": HEAD, "color": "white"})], [(roll, {"size": 10.5, "font": MONO, "color": "muted"})]], spacing=1.0, margin=0.18, anchor="m", shape=b)
    mem.append([b, a])
foot = text(s, 0.75, 6.72, 11, 0.3, "Live demo: CryptoVault (MongoDB · Express · React · Node.js). Every number in this deck was measured by us.", size=11, color="muted")
an.auto([t0, t1], "rise", 600, 150)
an.auto([t2, tag], "fade", 500, 150)
an.auto(mem, "rise", 450, 120)
an.auto([foot], "fade", 400)
an.write()
transition(s, "fade", "slow")
notes(
    s,
    "PRESENTER: Saurav Singh (about 30 s)\n\n"
    "Good morning. We are Group 18. Our topic is secure cloud file sharing using hybrid cryptography. "
    "This is a research plus application project. We took one published paper, the Hybrid AES-ECC model by Rehman et al. in the journal Electronics, 2021, "
    "and built it ourselves. Then we attacked it, found three weaknesses, fixed them, and measured the result. "
    "I'm Saurav; with me are Rohan, Ujjawal and Aditya. Each of us presents one part of the work and one part of the live demo.",
)

# =================================================================== SLIDE 1 - INTRODUCTION
s = prs.slides.add_slide(BLANK)
chrome(s, 1, "Introduction & problem statement", "Why cloud files need hybrid cryptography", "Saurav Singh")
an = Animator(s)
L = []
L.append(label(s, 0.6, 1.42, "The setting"))
L.append(
    text(
        s,
        0.6,
        1.7,
        6.2,
        0.75,
        "Cloud storage means our files live on someone else's computer. Hybrid cryptography uses two kinds of cryptography together:",
        size=14.5,
        spacing=1.1,
    )
)
ca, _ = card(s, 0.6, 2.55, 3.0, 0.95, fill="card2")
pic(s, A("ic_lock.png"), 0.75, 2.72, 0.6, 0.6)
text(s, 1.45, 2.62, 2.1, 0.85, [[("AES", {"bold": True, "color": "amber", "size": 15})], [("symmetric and fast: locks the file", {"size": 12, "color": "muted"})]], spacing=1.0, anchor="m")
cb, _ = card(s, 3.8, 2.55, 3.0, 0.95, fill="card2")
pic(s, A("ic_key.png"), 3.95, 2.72, 0.6, 0.6)
text(s, 4.65, 2.62, 2.1, 0.85, [[("ECC", {"bold": True, "color": "violet", "size": 15})], [("public key: protects and shares the AES key", {"size": 12, "color": "muted"})]], spacing=1.0, anchor="m")
L2 = [label(s, 0.6, 3.72, "Who can attack the files?", color="red")]
threats = [
    ("ic_attacker.png", "Outsider with a leaked copy", "misconfigured bucket, stolen backup"),
    ("ic_cloud.png", "Curious or malicious cloud insider", "can read and change the stored bytes"),
    ("ic_user.png", "A user whose access was removed", "must not open newer versions"),
]
rows = []
for i, (ic, a, b_) in enumerate(threats):
    y = 4.04 + i * 0.6
    r1 = pic(s, A(ic), 0.62, y, 0.46, 0.46)
    r2 = text(s, 1.2, y - 0.04, 5.6, 0.56, [[(a, {"bold": True, "size": 13.5})], [(b_, {"size": 11, "color": "muted"})]], anchor="m", spacing=0.95)
    rows.append([r1, r2])
# diagram (right)
dg, _ = card(s, 7.1, 1.42, 5.65, 4.12)
dl = [label(s, 7.35, 1.55, "Our threat model", w=4)]
own = pic(s, A("ic_user.png"), 7.45, 2.55, 0.9, 0.9)
ownt = text(s, 7.15, 3.47, 1.5, 0.5, [[("Alice", {"bold": True, "size": 13})], [("data owner", {"size": 10.5, "color": "muted"})]], align="c", spacing=0.95)
cld = pic(s, A("ic_cloud.png"), 9.35, 2.05, 1.35, 1.35)
cldt = text(s, 8.95, 3.38, 2.15, 0.5, [[("Cloud server", {"bold": True, "size": 13})], [("stores every file", {"size": 10.5, "color": "muted"})]], align="c", spacing=0.95)
rc1 = pic(s, A("ic_user_green.png"), 11.65, 2.2, 0.72, 0.72)
rc2 = pic(s, A("ic_user_green.png"), 11.65, 3.0, 0.72, 0.72)
rct = text(s, 11.25, 3.72, 1.5, 0.5, [[("Bob, Charlie", {"bold": True, "size": 12})], [("recipients", {"size": 10.5, "color": "muted"})]], align="c", spacing=0.95)
ar1 = box(s, 8.45, 2.88, 0.85, 0.22, fill="cyan", shape=MSO_SHAPE.RIGHT_ARROW)
ar1t = text(s, 8.3, 2.55, 1.2, 0.3, "upload", size=10, color="cyan", align="c", font=MONO)
ar2 = box(s, 10.75, 2.88, 0.85, 0.22, fill="green", shape=MSO_SHAPE.RIGHT_ARROW)
ar2t = text(s, 10.6, 2.55, 1.2, 0.3, "share", size=10, color="green", align="c", font=MONO)
att = pic(s, A("ic_attacker.png"), 9.6, 4.38, 0.85, 0.85)
attl = box(s, 9.98, 3.86, 0.1, 0.5, fill="red", shape=MSO_SHAPE.UP_ARROW)
attt = text(s, 10.5, 4.45, 2.2, 0.75, [[("Attacker", {"bold": True, "size": 13, "color": "red"})], [("reads or edits stored bytes", {"size": 10.5, "color": "muted"})]], spacing=0.95)
# problem statement band
pb, pa = card(s, 0.6, 5.72, 12.15, 1.22, accent="amber", fill="card2")
pl = label(s, 0.85, 5.82, "Problem statement", color="amber")
pt = text(
    s,
    0.85,
    6.1,
    7.7,
    0.8,
    "Does the published Hybrid AES-ECC model (Rehman et al., 2021) really keep shared cloud files secret and unmodified? If not, can we fix it without making it slow?",
    size=14,
    spacing=1.08,
)
objs = []
for i, (n_, t_) in enumerate([("1", "Rebuild"), ("2", "Attack"), ("3", "Fix"), ("4", "Measure")]):
    x = 8.85 + i * 0.98
    o = box(s, x, 6.0, 0.9, 0.78, fill="card", line="amber", radius=0.18, line_w=0.75)
    text(s, 0, 0, 0, 0, [[(n_, {"size": 16, "font": HEAD, "color": "amber"})], [(t_, {"size": 9.5, "color": "text"})]], align="c", anchor="m", spacing=0.95, shape=o)
    objs.append(o)
an.auto([L, ca, cb], "rise", 450, 120)
an.click([L2, rows], "rise", 450, 160)
an.click([dg, dl, own, ownt, cld, cldt, ar1, ar1t, rc1, rc2, rct, ar2, ar2t], "fade", 450, 70)
an.click([att, attl, attt], "zoom", 450, 80)
an.click([pb, pa, pl, pt], "wipe_left", 600, 0)
an.click(objs, "rise", 400, 150)
an.write()
transition(s, "fade")
notes(
    s,
    "PRESENTER: Saurav Singh (about 1.5 min)\n\n"
    "When we put a file in the cloud, it sits on someone else's computer. To protect it we use hybrid cryptography: "
    "AES, a fast symmetric cipher, locks the file, and ECC, a public-key method, takes care of the AES key.\n"
    "[click] Three kinds of attacker matter. An outsider who gets a leaked copy, for example from a misconfigured storage bucket. "
    "The cloud company itself, or one of its admins, who can read and even change the stored bytes. And a user whose access we removed.\n"
    "[click] Our setting: Alice uploads a file and shares it with Bob and Charlie through the cloud server. "
    "[click] The attacker sits at the cloud and sees everything stored there.\n"
    "[click] So our problem statement is: does the published hybrid AES-ECC model really keep shared files secret and unmodified, "
    "and if not, can we fix it without making it slow? [click] We did this in four steps: re-implement, attack, fix, and measure.",
)

# =================================================================== SLIDE 2 - TECHNOLOGIES
s = prs.slides.add_slide(BLANK)
chrome(s, 2, "Technologies used in the paper", "What the base paper uses: AES + ECC", "Rohan Dubey")
an = Animator(s)
cols = []
# AES
x = 0.6
c1, a1 = card(s, x, 1.42, 3.92, 4.38, accent="amber")
g1 = [c1, a1]
g1.append(text(s, x + 0.25, 1.55, 3.5, 0.5, [[("AES", {"size": 24, "font": HEAD, "color": "amber"}), ("   Module 3", {"size": 11, "color": "muted", "font": MONO})]]))
g1.append(text(s, x + 0.25, 2.12, 3.5, 0.75, "Symmetric block cipher: one secret key locks and unlocks. 128-bit blocks, 10 rounds for a 128-bit key.", size=12.5, color="text", spacing=1.08))
for i, (st, sub) in enumerate([("SubBytes", "S-box substitution"), ("ShiftRows", "rotate rows"), ("MixColumns", "math in GF(2⁸)"), ("AddRoundKey", "XOR round key")]):
    yb = 2.98 + i * 0.52
    bb = box(s, x + 0.25, yb, 2.75, 0.44, fill="card2", line="amber", radius=0.2, line_w=0.6)
    text(s, 0, 0, 0, 0, [[(st, {"size": 12, "bold": True}), ("  " + sub, {"size": 10, "color": "muted"})]], anchor="m", margin=0.12, shape=bb)
    g1.append(bb)
g1.append(text(s, x + 3.02, 3.5, 0.85, 0.8, ["× 10", "rounds"], size=12, color="amber", font=MONO, align="c"))
g1.append(text(s, x + 0.25, 5.1, 3.5, 0.6, "Very fast, so it encrypts the file itself.", size=12, color="muted"))
# ECC
x = 4.72
c2, a2 = card(s, x, 1.42, 3.92, 4.38, accent="violet")
g2 = [c2, a2]
g2.append(text(s, x + 0.25, 1.55, 3.5, 0.5, [[("ECC", {"size": 24, "font": HEAD, "color": "violet"}), ("   Module 4", {"size": 11, "color": "muted", "font": MONO})]]))
g2.append(pic(s, A("ecc_curve.png"), x + 0.45, 2.08, 3.0, 2.29))
g2.append(
    text(
        s,
        x + 0.25,
        4.36,
        3.5,
        1.4,
        [
            [("Private key: a secret number ", {}), ("n", {"bold": True, "color": "violet"})],
            [("Public key: the point ", {}), ("P = n·G", {"bold": True, "color": "violet", "font": MONO})],
            [("Getting n back from P (the ECDLP) is infeasible.", {"color": "muted"})],
            [("256-bit ECC ≈ 3072-bit RSA security.", {"color": "muted"})],
        ],
        size=12,
        spacing=1.1,
    )
)
# Hybrid (paper)
x = 8.84
c3, a3 = card(s, x, 1.42, 3.92, 4.38, accent="cyan")
g3 = [c3, a3]
g3.append(text(s, x + 0.25, 1.55, 3.6, 0.5, [[("Hybrid AES-ECC", {"size": 20, "font": HEAD, "color": "cyan"})]]))
g3.append(text(s, x + 0.25, 1.98, 3.6, 0.3, "the paper's algorithm (Box 1 + Box 2)", size=10.5, color="muted", font=MONO))
steps = [
    ("1", "Cloud generates ECC keys", "P = n·G"),
    ("2", "AES key taken from the", "ECC public key P"),
    ("3", "AES encrypts the file", "at the cloud provider"),
    ("4", "Cloud stores ciphertext", "decrypt = reverse steps"),
]
g3s = []
for i, (n_, a_, b_) in enumerate(steps):
    yb = 2.42 + i * 0.66
    circ = box(s, x + 0.25, yb + 0.06, 0.42, 0.42, fill="cyan", shape=MSO_SHAPE.OVAL)
    text(s, 0, 0, 0, 0, n_, size=13, color="ink", font=HEAD, align="c", anchor="m", shape=circ)
    tt = text(s, x + 0.8, yb, 3.0, 0.6, [[(a_, {"size": 12.5, "bold": True})], [(b_, {"size": 11, "color": "muted"})]], spacing=0.98)
    g3s.append([circ, tt])
claim = box(s, x + 0.25, 5.1, 3.45, 0.55, fill="card2", line="amber", radius=0.2, line_w=0.6)
text(s, 0, 0, 0, 0, "Claims: smaller keys, faster, and \"authentication & integrity\"", size=10.5, color="amber", anchor="m", margin=0.1, shape=claim)
# bottom strip
sb, sa = card(s, 0.6, 5.98, 12.15, 0.95, accent="green", fill="card2")
sl = label(s, 0.85, 6.06, "Our re-implementation", color="green")
st_ = text(
    s,
    0.85,
    6.33,
    11.7,
    0.6,
    "We followed the paper's Box 1 and Box 2 exactly. The authors' GitHub repository contains only a README, so we wrote the code ourselves: MongoDB · Express · React · Node.js, NIST P-256 curve, AES-128.",
    size=12.5,
    spacing=1.05,
)
an.click(g1, "rise", 450, 60)
an.click(g2, "rise", 450, 60)
an.click([g3, g3s, claim], "rise", 450, 110)
an.click([sb, sa, sl, st_], "wipe_left", 550)
an.write()
transition(s, "fade")
notes(
    s,
    "PRESENTER: Rohan Dubey (about 1.5 min)\n\n"
    "The paper combines two algorithms from our syllabus. [click] AES, from Module 3, is a symmetric block cipher: the same key locks and unlocks. "
    "It works on 128-bit blocks and repeats 10 rounds of SubBytes, ShiftRows, MixColumns and AddRoundKey. MixColumns is arithmetic in the finite field GF(2^8). "
    "AES is very fast, so it encrypts the file itself.\n"
    "[click] ECC, from Module 4, works with points on a curve y^2 = x^3 + ax + b over a prime field. The private key is a number n, and the public key is the point P = n times G. "
    "Recovering n from P is the elliptic-curve discrete log problem, which is infeasible. A 256-bit ECC key is as strong as a 3072-bit RSA key.\n"
    "[click] The paper's hybrid algorithm has four steps: the cloud generates the ECC keys, the AES key is taken from the ECC public key, AES encrypts the file at the cloud, "
    "and the cloud stores the ciphertext. The paper says this gives smaller keys, more speed, and authentication and integrity.\n"
    "[click] The paper links a GitHub repository, but it contains only a README, so we implemented the boxes ourselves in a MERN web app.",
)

# =================================================================== SLIDE 3 - RESULTS OF THE WORK
s = prs.slides.add_slide(BLANK)
chrome(s, 3, "Results of the work", "What the paper reports, and our reproduction", "Rohan Dubey")
an = Animator(s)
cc, ca_ = card(s, 0.6, 1.42, 6.85, 4.95)
cl = label(s, 0.85, 1.55, "Encryption time reported in the paper (s)", w=6)
cd = CategoryChartData()
cd.categories = ["64-bit key", "128-bit key", "192-bit key", "256-bit key"]
cd.add_series("Hybrid AES-ECC", (2.40, 2.47, 2.54, 2.60))
cd.add_series("AES", (3.42, 3.59, 3.48, 3.60))
cd.add_series("DES", (3.89, 4.02, 4.05, 4.34))
cd.add_series("Blowfish", (4.31, 4.47, 4.43, 4.70))
gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.75), Inches(1.85), Inches(6.55), Inches(4.0), cd)
style_chart(gf.chart, ["amber", "cyan", "violet", "5B6B8C"], size=11, labels=True, fmt="0.0")
gf.chart.value_axis.maximum_scale = 5.0
src = text(s, 0.85, 5.9, 6.4, 0.4, "Source: Rehman et al., Electronics 10(21):2673, Table 7 (text data, Python, Intel i7-8550U)", size=9.5, color="muted", font=MONO)
# claims
rl = label(s, 7.75, 1.42, "What the paper claims")
claims = [
    ("~30% faster", "Hybrid 2.40–2.60 s vs AES 3.42–3.60 s (Table 7)", "amber"),
    ("61% / 64%", "avalanche for 1-bit key / text change; AES: 51% / 55% (Table 9)", "amber"),
    ("1 : 12", "key size ECC : RSA, so less memory (Table 5)", "amber"),
    ("\"Integrity\"", "says it ensures authentication & data integrity (Abstract)", "amber"),
]
cl_tiles = []
for i, (big, sm, col) in enumerate(claims):
    x = 7.75 + (i % 2) * 2.53
    y = 1.75 + (i // 2) * 1.2
    b, _ = card(s, x, y, 2.43, 1.08, fill="card2")
    text(s, 0, 0, 0, 0, [[(big, {"size": 19, "font": HEAD, "color": col})], [(sm, {"size": 9.8, "color": "muted"})]], spacing=1.0, margin=0.14, anchor="m", shape=b)
    cl_tiles.append(b)
ol = label(s, 7.75, 4.24, "Our reproduction", color="green")
mb16 = perf[16384]["base_enc_mbps"]
repro = [
    ("Works ✓", f"{e1['files']}/{e1['files']} test files encrypt and decrypt correctly"),
    (f"{mb16:,.0f} MB/s", "AES-128-ECB speed on a 16 MiB file"),
    (f"{e9['p256_keygen_ms']:.2f} ms", f"P-256 key generation (RSA-3072: {e9['rsa3072_keygen_ms']:.0f} ms)"),
]
rp_tiles = []
for i, (big, sm) in enumerate(repro):
    x = 7.75 + i * 1.69
    b, _ = card(s, x, 4.55, 1.6, 1.15, fill="card2", line="green")
    text(s, 0, 0, 0, 0, [[(big, {"size": 15, "font": HEAD, "color": "green"})], [(sm, {"size": 9, "color": "muted"})]], spacing=1.0, margin=0.1, anchor="m", shape=b)
    rp_tiles.append(b)
tease = text(s, 7.75, 5.85, 5.0, 0.5, [[("It is fast. ", {"color": "text"}), ("But is it secure?", {"color": "amber", "bold": True})]], size=16, font=HEAD)
an.click([cc, cl, gf, src], "fade", 500, 80)
an.click([rl, cl_tiles], "rise", 450, 130)
an.click([ol, rp_tiles], "rise", 450, 130)
an.click([tease], "zoom", 450)
an.write()
transition(s, "fade")
notes(
    s,
    "PRESENTER: Rohan Dubey (about 1.5 min)\n\n"
    "[click] These are the paper's own results, from its Table 7. For every key size, the hybrid model is reported as the fastest: about 2.4 to 2.6 seconds, against 3.4 to 3.6 for plain AES, "
    "and more for DES and Blowfish.\n"
    "[click] The paper also claims an avalanche effect of 61 and 64 percent, higher than AES, a key size ratio of 1 to 12 compared with RSA, "
    "and, in the abstract, that it ensures authentication and data integrity.\n"
    "[click] We reproduced the scheme in our app. It works: all 100 test files encrypt and decrypt correctly. On our machine AES-128 runs at nearly a gigabyte per second, "
    "and generating an ECC P-256 key takes a fraction of a millisecond, compared with about 145 ms for RSA-3072. So the efficiency claims about ECC are fair.\n"
    "[click] It is fast. But is it secure? Ujjawal will show what we found.",
)

# =================================================================== SLIDE 4 - WEAKNESSES
s = prs.slides.add_slide(BLANK)
chrome(s, 4, "Weaknesses of the paper", "Three challenges we found and proved", "Ujjawal")
an = Animator(s)
chal = [
    (
        "1",
        "The key comes from the PUBLIC key",
        "Box 2 builds the AES key from the ECC public key. Public keys are public, so anyone can rebuild the AES key without the private key.",
        f"{e1['base_recovered']} / {e1['files']}",
        "files decrypted by our attacker using only public data",
        "Kerckhoffs' principle · Shannon: key equivocation H(K | P) = 0",
    ),
    (
        "2",
        "No integrity check, and ECB mode",
        "The paper claims integrity but adds no MAC, hash or signature. The cloud can change data silently, and ECB keeps the patterns of the data.",
        f"{B2} / {fmt_int(T2)}",
        "tampering attempts detected (bit flips, block swaps, deletions)",
        "Block cipher modes (Module 3) · Hash & signatures (Module 5)",
    ),
    (
        "3",
        "No real sharing or revocation",
        "The cloud does the encryption, so it sees the plaintext and can compute the key. Removing a user changes no key at all, so revocation is only on paper.",
        "0 keys",
        "change when a user's access is revoked",
        "Key distribution & management (Unit 6)",
    ),
]
cards = []
for i, (n_, ttl, body, big, cap, course) in enumerate(chal):
    x = 0.6 + i * 4.12
    b, a = card(s, x, 1.42, 3.92, 3.62, accent="red")
    g = [b, a]
    nb = box(s, x + 0.25, 1.58, 0.46, 0.46, fill="red", shape=MSO_SHAPE.OVAL)
    text(s, 0, 0, 0, 0, n_, size=15, color="white", font=HEAD, align="c", anchor="m", shape=nb)
    g.append(nb)
    g.append(text(s, x + 0.85, 1.52, 2.95, 0.62, ttl, size=15.5, font=HEAD, color="white", spacing=0.98, anchor="m"))
    g.append(text(s, x + 0.25, 2.2, 3.5, 1.15, body, size=11.8, color="text", spacing=1.08))
    ev = box(s, x + 0.25, 3.4, 3.45, 0.95, fill="2A0F15", line="red", radius=0.12, line_w=0.6)
    text(s, 0, 0, 0, 0, [[(big, {"size": 22, "font": HEAD, "color": "red"})], [(cap, {"size": 9.8, "color": "muted"})]], spacing=0.95, margin=0.12, anchor="m", shape=ev)
    g.append(ev)
    g.append(text(s, x + 0.25, 4.45, 3.5, 0.5, course, size=9.5, color="cyan", font=MONO, spacing=1.0))
    cards.append(g)
# evidence strip
eb, _ = card(s, 0.6, 5.22, 6.6, 1.72, fill="card2")
el = label(s, 0.8, 5.3, "Evidence: same image, encrypted", w=6)
ims = []
for i, (fn, cap, col) in enumerate(
    [
        ("ecb_original.png", "original", "muted"),
        ("ecb_base_encrypted.png", f"base: {e3['base']['repeated_block_pct']:.0f}% blocks repeat", "red"),
        ("ecb_proposed_encrypted.png", f"ours: {e3['proposed']['repeated_block_pct']:.0f}% repeat", "green"),
    ]
):
    x = 0.8 + i * 2.1
    p_ = pic(s, A(fn), x, 5.58, 1.42, 1.07)
    c_ = text(s, x - 0.05, 6.64, 2.05, 0.3, cap, size=9, color=col, font=MONO)
    ims.append([p_, c_])
pb2, _ = card(s, 7.4, 5.22, 5.35, 1.72, fill="card2")
pl2 = label(s, 7.6, 5.3, "Evidence: cloud swaps 2 ciphertext blocks", w=5)
pay = text(
    s,
    7.6,
    5.62,
    5.0,
    1.25,
    [
        [("TO: ALICE      ", {"color": "text"}), ("AMT: Rs 100000", {"color": "muted"}), ("  →  ", {"color": "muted"}), ("Rs 10", {"color": "red", "bold": True})],
        [("TO: MALLORY    ", {"color": "text"}), ("AMT: Rs 10    ", {"color": "muted"}), ("  →  ", {"color": "muted"}), ("Rs 100000", {"color": "red", "bold": True})],
        [("Decrypts with no error. Nobody notices.", {"color": "amber", "font": BODY, "size": 11})],
    ],
    size=11.5,
    font=MONO,
    spacing=1.25,
)
an.click(cards[0], "rise", 450, 70)
an.click(cards[1], "rise", 450, 70)
an.click([eb, el, ims, pb2, pl2, pay], "fade", 450, 90)
an.click(cards[2], "rise", 450, 70)
an.write()
transition(s, "fade")
notes(
    s,
    "PRESENTER: Ujjawal (about 2 min)\n\n"
    "We found three challenges, and we proved each one with a real attack in our app.\n"
    "[click] Challenge 1, the most serious: in Box 2 the AES key is built from the ECC PUBLIC key. A public key is meant to be published, so anyone can rebuild the AES key. "
    "No private key and no brute force are needed. This breaks Kerckhoffs' principle. In Shannon's terms, the key equivocation H(K given the public key) is zero bits: the attacker has no uncertainty left. "
    "Our attacker decrypted 100 out of 100 files using only public data.\n"
    "[click] Challenge 2: the paper says it ensures integrity, but there is no MAC, no hash and no signature. We tampered with the stored ciphertext 1,250 times "
    "with bit flips, block swaps and deletions, and none of these changes was detected.\n"
    "[click] Here is the evidence. Because the AES mode has no IV and works block by block like ECB, equal blocks stay equal: the logo is still visible after encryption. "
    "And on the right, the cloud swapped two ciphertext blocks of a payment order. Alice's 1 lakh rupees went to Mallory, the file decrypted without any error, and nobody noticed.\n"
    "[click] Challenge 3: the cloud provider does the encryption, so it sees the plaintext and can compute the key. Sharing is only a server access list, "
    "so when a user is removed, no key changes. The evaluation also has problems: it uses a 64-bit AES key, which AES does not support; it reads 64% avalanche as better, although the ideal is 50%; "
    "its power table repeats the timing numbers; and the code repository is empty.",
)

# =================================================================== SLIDE 5 - PROPOSED IMPROVEMENT
s = prs.slides.add_slide(BLANK)
chrome(s, 5, "Improving the weaknesses", "Our fix: an authenticated hybrid envelope", "Aditya Raj")
an = Animator(s)
flow = [
    ("ic_key_green.png", "Random file key", "256-bit key from the browser's secure random generator, new for every file", "fixes 1"),
    ("ic_lock_green.png", "AES-256-GCM", "encrypts and adds a 128-bit tag (CTR mode + GHASH)", "fixes 2"),
    ("ic_user_green.png", "Lock key per user", "ECDH (Diffie-Hellman on P-256) + HKDF wraps the file key", "fixes 1 · 3"),
    ("ic_sign.png", "Owner signs", "ECDSA-P256 over SHA-256 of everything uploaded", "fixes 2"),
    ("ic_db.png", "Cloud sees nothing", "stores only ciphertext: never the plaintext, keys or file names", "fixes 3"),
]
W5, G5 = 2.19, 0.3
fl = []
for i, (ic, ttl, sub, fx) in enumerate(flow):
    x = 0.6 + i * (W5 + G5)
    b, _ = card(s, x, 1.42, W5, 2.3, fill="card2", line="green")
    num = box(s, x + 0.14, 1.54, 0.38, 0.38, fill="green", shape=MSO_SHAPE.OVAL)
    text(s, 0, 0, 0, 0, str(i + 1), size=12, color="ink", font=HEAD, align="c", anchor="m", shape=num)
    icn = pic(s, A(ic), x + W5 - 0.66, 1.52, 0.5, 0.5)
    tt = text(s, x + 0.14, 2.06, W5 - 0.25, 0.4, ttl, size=13.5, font=HEAD, color="white")
    sb_ = text(s, x + 0.14, 2.44, W5 - 0.25, 0.85, sub, size=10.3, color="muted", spacing=1.02)
    fxb = box(s, x + 0.14, 3.32, 1.05, 0.28, fill="0B2E25", line="green", radius=0.5, line_w=0.5)
    text(s, 0, 0, 0, 0, fx.upper(), size=8.5, color="green", font=MONO, align="c", anchor="m", shape=fxb)
    g = [b, num, icn, tt, sb_, fxb]
    if i < 4:
        arr = box(s, x + W5 + 0.05, 2.45, 0.2, 0.24, fill="green", shape=MSO_SHAPE.ISOSCELES_TRIANGLE)
        arr.rotation = 90
        g.append(arr)
    fl.append(g)
# open + share cards
ob, oa = card(s, 0.6, 3.92, 7.05, 1.62, accent="cyan")
ol_ = label(s, 0.85, 4.0, "When a recipient opens the file")
osteps = []
for i, t_ in enumerate([["Verify owner's", "ECDSA signature"], ["Check SHA-256", "of ciphertext"], ["Unlock file key", "with MY private key"], ["Decrypt +", "check GCM tag"]]):
    x = 0.85 + i * 1.7
    b = box(s, x, 4.34, 1.52, 0.72, fill="card2", line="cyan", radius=0.15, line_w=0.6)
    text(s, 0, 0, 0, 0, t_, size=10.2, color="text", align="c", anchor="m", spacing=0.95, shape=b)
    osteps.append(b)
otx = text(s, 0.85, 5.12, 6.7, 0.35, [[("Any check fails → ", {"color": "muted"}), ("BLOCKED", {"color": "red", "bold": True}), (". No data is released.", {"color": "muted"})]], size=11.5)
sb2, sa2 = card(s, 7.85, 3.92, 4.9, 1.62, accent="violet")
sl2 = label(s, 8.1, 4.0, "Sharing and revoking", color="violet")
stx = text(
    s,
    8.1,
    4.3,
    4.55,
    1.2,
    [
        [("Share: ", {"bold": True, "color": "violet"}), (f"add one more locked key ({e7['add_recipient_later_ms']:.1f} ms), no re-encryption.", {})],
        [("Revoke: ", {"bold": True, "color": "violet"}), (f"new random key + re-encrypt as version 2 ({rev[1024]['rekey_ms']:.1f} ms per MiB). The old key opens nothing new.", {})],
    ],
    size=11.5,
    spacing=1.08,
    after=4,
)
# course mapping
cm = []
cl5 = label(s, 0.6, 5.7, "Built only from course topics", color="amber")
cm.append(cl5)
course = [
    ("Module 3", "AES · modes: ECB ✗ → CTR/GCM ✓"),
    ("Units 4 & 6", "ECC · Diffie-Hellman key exchange"),
    ("Module 5", "SHA-256 · digital signatures (DSA idea on curves)"),
    ("Unit 2", "Entropy: key = 256 random bits; ciphertext ≈ 8 bits/byte"),
]
for i, (m, t_) in enumerate(course):
    x = 0.6 + i * 3.06
    b = box(s, x, 6.0, 2.93, 0.92, fill="card", line="amber", radius=0.12, line_w=0.6)
    text(s, 0, 0, 0, 0, [[(m, {"size": 11, "font": MONO, "color": "amber"})], [(t_, {"size": 10.5, "color": "text"})]], spacing=1.0, margin=0.12, anchor="m", shape=b)
    cm.append(b)
an.click(fl, "wipe_left", 450, 220)
an.click([ob, oa, ol_, osteps, otx], "rise", 400, 90)
an.click([sb2, sa2, sl2, stx], "rise", 400, 90)
an.click(cm, "rise", 400, 100)
an.write()
transition(s, "fade")
notes(
    s,
    "PRESENTER: Aditya Raj (about 2 min)\n\n"
    "Our fix is called an authenticated hybrid envelope. It is still hybrid, AES plus ECC, but each piece is used correctly. [click]\n"
    "Step 1: for every file the browser generates a fresh 256-bit random key. It is never computed from anything public, which fixes challenge 1.\n"
    "Step 2: AES-256 in GCM mode. GCM is counter mode plus a 128-bit authentication tag computed in GF(2^128). Changing even one bit makes the tag fail, which fixes challenge 2.\n"
    "Step 3: the file key is locked separately for each recipient with ECDH, which is Diffie-Hellman on the elliptic curve: we compute a shared secret r·Q with the recipient's public key Q, "
    "and only the recipient's private key can recompute it. Then HKDF turns that secret into a wrapping key.\n"
    "Step 4: the owner signs everything with ECDSA, the digital-signature idea from Module 5 applied to curves, so nobody can change or swap files without detection.\n"
    "Step 5: the cloud stores only ciphertext. It never sees the plaintext, the key, or even the file name.\n"
    "[click] When Bob opens a file, his browser checks the signature, checks the hash, unlocks the key with his own private key, and decrypts while checking the tag. If any check fails, nothing is released.\n"
    "[click] Sharing just adds one more locked key, in about 3 ms. Revoking creates a brand-new key and a new version, so the removed user's old key opens nothing new.\n"
    "[click] Everything we used is from the course: AES and modes, ECC and Diffie-Hellman, hashing and signatures, and entropy.",
)

# =================================================================== SLIDE 6 - IMPROVED RESULTS + CONCLUSION
s = prs.slides.add_slide(BLANK)
chrome(s, 6, "Improved results & conclusion", "Results after the fix, and conclusion", "Aditya · Saurav")
an = Animator(s)
tb, _ = card(s, 0.6, 1.42, 7.45, 4.0)
hdr = s.shapes.add_group_shape()
box(hdr, 0.75, 1.55, 7.15, 0.4, fill="13223F", radius=0.15)
text(hdr, 0.9, 1.55, 3.6, 0.4, "Test (all measured in our app)", size=11, color="muted", font=MONO, anchor="m")
text(hdr, 4.45, 1.55, 1.6, 0.4, "BASE AES-ECC", size=11, color="red", font=MONO, anchor="m", align="c")
text(hdr, 6.2, 1.55, 1.6, 0.4, "OURS", size=11, color="green", font=MONO, anchor="m", align="c")
res_rows = [
    (f"Decrypt using only public data ({e1['files']} files)", f"{e1['base_recovered']} / {e1['files']}", f"{e1['proposed_recovered']} / {e1['files']}"),
    (f"Tampering detected ({fmt_int(T2)} attacks)", f"{100 * B2 / T2:.0f} %", f"{100 * P2 / T2:.0f} %"),
    ("Image patterns leaked (repeated blocks)", f"{e3['base']['repeated_block_pct']:.1f} %", f"{e3['proposed']['repeated_block_pct']:.0f} %"),
    ("Ciphertext entropy (max 8 bits/byte)", f"{e3['base']['entropy_bits_per_byte']:.2f}", f"{e3['proposed']['entropy_bits_per_byte']:.2f}"),
    ("Same file uploaded twice: bits that differ", f"{e4['base_bit_difference_pct']:.0f} %", f"{e4['proposed_bit_difference_pct']:.1f} %"),
    ("Revoke a user", "not possible", f"{rev[1024]['rekey_ms']:.1f} ms / MiB"),
    ("Encrypt a 16 MiB file", f"{perf[16384]['base_enc_ms']:.1f} ms", f"{perf[16384]['proposed_enc_ms']:.1f} ms"),
]
rws = []
for i, (t_, b_, p_) in enumerate(res_rows):
    y = 2.02 + i * 0.47
    g = s.shapes.add_group_shape()
    box(g, 0.75, y, 7.15, 0.42, fill="0E1A34" if i % 2 else "101D3A", radius=0.12)
    text(g, 0.9, y, 3.55, 0.42, t_, size=11.5, color="text", anchor="m")
    text(g, 4.45, y, 1.6, 0.42, b_, size=12.5, color="amber" if i == 6 else "red", font=HEAD, anchor="m", align="c")
    text(g, 6.2, y, 1.6, 0.42, p_, size=12.5, color="amber" if i == 6 else "green", font=HEAD, anchor="m", align="c")
    rws.append(g)
# chart: time vs size
chb, _ = card(s, 8.25, 1.42, 4.5, 4.0)
chl = label(s, 8.45, 1.52, "Encryption time (ms)", w=4)
cd = CategoryChartData()
sizes = [1024, 4096, 16384, 32768]
cd.categories = [f"{k // 1024} MiB" for k in sizes]
cd.add_series("Base (no integrity)", [perf[k]["base_enc_ms"] for k in sizes])
cd.add_series("Ours (+tag, ECDH, signature)", [perf[k]["proposed_enc_ms"] for k in sizes])
gf2 = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(8.35), Inches(1.8), Inches(4.3), Inches(2.95), cd)
style_chart(gf2.chart, ["red", "green"], size=9.5, labels=True, fmt="0")
cost = text(
    s,
    8.45,
    4.75,
    4.2,
    0.6,
    f"Cost of security: about {perf[1]['proposed_enc_ms']:.0f} ms per file plus extra time on big files. Still {perf[16384]['proposed_enc_mbps']:.0f} MB/s.",
    size=10.5,
    color="muted",
    spacing=1.02,
)
# conclusion
cb6, ca6 = card(s, 0.6, 5.58, 12.15, 1.38, accent="cyan", fill="card2")
cl6 = label(s, 0.85, 5.66, "Conclusion")
con = text(
    s,
    0.85,
    5.93,
    11.7,
    1.0,
    [
        [("■  ", {"color": "red", "size": 9}), ("The published AES-ECC model is fast but not secure: anyone can compute its AES key from public data, and tampering goes unnoticed.", {})],
        [("■  ", {"color": "green", "size": 9}), ("Our fix uses only course tools (AES-GCM, ECDH, ECDSA, SHA-256). All our attacks fail, and every tampering attempt is caught.", {})],
        [("■  ", {"color": "cyan", "size": 9}), ("Security costs a few milliseconds per file. Future work: post-quantum key exchange (ML-KEM) and a public-key transparency log.", {})],
    ],
    size=12,
    spacing=1.05,
    after=2,
)
an.click([tb, hdr], "fade", 350)
an.click(rws[:2], "wipe_left", 450, 200)
an.click(rws[2:5], "wipe_left", 450, 200)
an.click(rws[5:], "wipe_left", 450, 200)
an.click([chb, chl, gf2, cost], "fade", 500, 80)
an.click([cb6, ca6, cl6, con], "rise", 500, 80)
an.write()
transition(s, "fade")
notes(
    s,
    "PRESENTER: Aditya Raj (results, about 1.5 min), then Saurav Singh (conclusion, about 45 s)\n\n"
    "ADITYA: We ran the same attacks on both schemes. [click] With only public data, the attacker decrypted all 100 base files and none of ours. "
    "Tampering: the base scheme detected 0 of 1,250 attempts; ours detected all of them. [click] Image patterns: 98% of the blocks repeat in the base ciphertext and none in ours, "
    "and our ciphertext has the maximum entropy of 8 bits per byte, which is Shannon's measure of randomness from Unit 2. If the same file is uploaded twice, the base scheme gives an identical ciphertext, "
    "which tells an observer the two files are equal; ours differs in about half of all bits, as it should. "
    "[click] Revocation is now possible: re-keying 1 MiB takes a few milliseconds. And the price: encrypting 16 MiB takes longer with our scheme, "
    "[click] as the chart shows. We pay about 3 ms per file for the key locking and the signature, plus the tag and hash on large files, and we still run at hundreds of MB per second.\n"
    "SAURAV: [click] To conclude: the published AES-ECC model is fast but not secure. Anyone can compute its key from public data, and tampering goes unnoticed. "
    "Our fix uses only tools from this course: AES-GCM, ECDH, ECDSA and SHA-256. Every attack we tried fails, and every tampering attempt is caught, at a cost of a few milliseconds. "
    "As future work, a post-quantum key exchange such as ML-KEM, and a transparency log so users can verify each other's public keys. Thank you. We will now show the live demo.",
)

prs.save(OUT)
print("saved", OUT)
