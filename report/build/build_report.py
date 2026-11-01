"""Builds the Group 18 project report (.docx) with python-docx.
usage: python3 build_report.py <results.json> <figures_dir> <screenshots_dir> <out.docx>"""
import json
import re
import sys

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

RES, FIG, SHOT, OUT = sys.argv[1:5]
R = json.load(open(RES))
e1 = R["e1_public_key_attack"]
e2 = R["e2_tampering"]
T2 = sum(v["trials"] for v in e2.values())
B2 = sum(v["base"]["detected"] for v in e2.values())
P2 = sum(v["proposed"]["detected"] for v in e2.values())
BS2 = sum(v["base"]["silent_corruption"] for v in e2.values())
e3 = R["e3_ecb_image"]
e4 = R["e4_determinism"]
e5 = R["e5_avalanche"]
perf = {r["size_kib"]: r for r in R["e6_performance"]}
e7 = R["e7_sharing"]
rev = {r["size_kib"]: r for r in R["e8_revocation"]}
e9 = R["e9_primitives"]
meta = R["meta"]

NAVY = RGBColor(0x0B, 0x2E, 0x4F)
TEAL = RGBColor(0x0E, 0x7C, 0x86)
GREY = RGBColor(0x55, 0x60, 0x70)
BODY_FONT = "Cambria"
HEAD_FONT = "Calibri"
MONO = "Consolas"

doc = Document()
sec = doc.sections[0]
sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
sec.left_margin = sec.right_margin = Cm(2.3)
sec.top_margin, sec.bottom_margin = Cm(2.2), Cm(2.2)

st = doc.styles["Normal"]
st.font.name = BODY_FONT
st.font.size = Pt(11)
st.element.rPr.rFonts.set(qn("w:eastAsia"), BODY_FONT)
st.paragraph_format.space_after = Pt(6)
st.paragraph_format.line_spacing = 1.15
for lvl, size, col in [(1, 16, NAVY), (2, 13, TEAL), (3, 11.5, NAVY)]:
    h = doc.styles[f"Heading {lvl}"]
    h.font.name = HEAD_FONT
    h.font.size = Pt(size)
    h.font.bold = True
    h.font.color.rgb = col
    h.element.rPr.rFonts.set(qn("w:eastAsia"), HEAD_FONT)
    h.element.rPr.rFonts.set(qn("w:ascii"), HEAD_FONT)
    h.element.rPr.rFonts.set(qn("w:hAnsi"), HEAD_FONT)
    h.paragraph_format.space_before = Pt(14 if lvl == 1 else 10)
    h.paragraph_format.space_after = Pt(6)
    h.paragraph_format.keep_with_next = True

FIGN = [0]
TABN = [0]


# ------------------------------------------------------------------ helpers
def add_runs(p, txt, size=None, color=None):
    # **bold**, `code`, _italic_
    for part in re.split(r"(\*\*[^*]+\*\*|`[^`]+`|(?<![\w])_[^_]+_(?![\w]))", txt):
        if not part:
            continue
        if part.startswith("**"):
            r = p.add_run(part[2:-2])
            r.bold = True
        elif part.startswith("`"):
            r = p.add_run(part[1:-1])
            r.font.name = MONO
            r.font.size = Pt((size or 11) - 1.5)
        elif part.startswith("_") and part.endswith("_") and len(part) > 2:
            r = p.add_run(part[1:-1])
            r.italic = True
        else:
            r = p.add_run(part)
        if size and not part.startswith("`"):
            r.font.size = Pt(size)
        if color:
            r.font.color.rgb = color
    return p


def P(txt, align="j", size=None, after=None, color=None, indent=None):
    p = doc.add_paragraph()
    p.alignment = {"j": WD_ALIGN_PARAGRAPH.JUSTIFY, "l": WD_ALIGN_PARAGRAPH.LEFT, "c": WD_ALIGN_PARAGRAPH.CENTER}[align]
    if after is not None:
        p.paragraph_format.space_after = Pt(after)
    if indent:
        p.paragraph_format.left_indent = Cm(indent)
    add_runs(p, txt, size, color)
    return p


def H(txt, lvl=1):
    return doc.add_heading(txt, lvl)


def bullets(items, style="List Bullet"):
    for it in items:
        p = doc.add_paragraph(style=style)
        p.paragraph_format.space_after = Pt(3)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        add_runs(p, it)


def numbered(items):
    # manual numbering so every list restarts at 1
    for i, it in enumerate(items, 1):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.9)
        p.paragraph_format.first_line_indent = Cm(-0.6)
        p.paragraph_format.space_after = Pt(3)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        add_runs(p, f"{i}.  " + it)


def shade(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear")
    sh.set(qn("w:color"), "auto")
    sh.set(qn("w:fill"), hexcolor)
    tcPr.append(sh)


def caption(txt, kind="Figure"):
    if kind == "Figure":
        FIGN[0] += 1
        n = FIGN[0]
    else:
        TABN[0] += 1
        n = TABN[0]
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(10)
    r = p.add_run(f"{kind} {n}. ")
    r.bold = True
    r.font.size = Pt(9.5)
    r.font.color.rgb = NAVY
    add_runs(p, txt, 9.5, GREY)
    return n


def table(header, rows, widths=None, size=9.5, caption_txt=None, align_first="l"):
    if caption_txt:
        # table captions go above
        TABN[0] += 1
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.keep_with_next = True
        r = p.add_run(f"Table {TABN[0]}. ")
        r.bold = True
        r.font.size = Pt(9.5)
        r.font.color.rgb = NAVY
        add_runs(p, caption_txt, 9.5, GREY)
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    trPr = t.rows[0]._tr.get_or_add_trPr()
    th = OxmlElement("w:tblHeader")
    th.set(qn("w:val"), "true")
    trPr.append(th)
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]
        c.text = ""
        add_runs(c.paragraphs[0], f"**{h}**", size, RGBColor(0xFF, 0xFF, 0xFF))
        shade(c, "0B2E4F")
    for ri, row in enumerate(rows):
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            add_runs(cells[i].paragraphs[0], str(v), size)
            if ri % 2:
                shade(cells[i], "EEF3F8")
    for row in t.rows:
        for c in row.cells:
            for p in c.paragraphs:
                p.paragraph_format.space_after = Pt(1)
                p.paragraph_format.line_spacing = 1.0
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def figure(path, width_cm, cap):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.space_after = Pt(2)
    p.add_run().add_picture(path, width=Cm(width_cm))
    return caption(cap)


def code(lines):
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    c = t.rows[0].cells[0]
    shade(c, "F3F6FA")
    c.text = ""
    p = c.paragraphs[0]
    for i, ln in enumerate(lines):
        r = p.add_run(ln)
        r.font.name = MONO
        r.font.size = Pt(8.8)
        if i < len(lines) - 1:
            r.add_break()
    p.paragraph_format.line_spacing = 1.0
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def page_break():
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def field(paragraph, instr):
    r = paragraph.add_run()
    f1 = OxmlElement("w:fldChar")
    f1.set(qn("w:fldCharType"), "begin")
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = instr
    f2 = OxmlElement("w:fldChar")
    f2.set(qn("w:fldCharType"), "separate")
    t = OxmlElement("w:t")
    t.text = "(right-click → Update Field)"
    f3 = OxmlElement("w:fldChar")
    f3.set(qn("w:fldCharType"), "end")
    r._r.append(f1)
    r._r.append(it)
    r._r.append(f2)
    r._r.append(t)
    r._r.append(f3)


# ================================================================== COVER
for _ in range(3):
    doc.add_paragraph()
P("CRYPTOGRAPHY  ·  COURSE PROJECT REPORT", "c", 11, color=TEAL)
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("Secure Cloud File Sharing\nUsing Hybrid Cryptography")
r.font.name = HEAD_FONT
r.font.size = Pt(28)
r.bold = True
r.font.color.rgb = NAVY
P(
    "Re-implementation, security analysis and improvement of the Hybrid AES-ECC model of Rehman et al. (Electronics, 2021)",
    "c",
    13,
    color=GREY,
)
P("Project type: Research + Application", "c", 11, color=TEAL, after=30)
P("**Group 18**", "c", 13)
t = doc.add_table(rows=1, cols=2)
t.style = "Table Grid"
t.alignment = WD_TABLE_ALIGNMENT.CENTER
for i, h in enumerate(["Name", "Roll number"]):
    c = t.rows[0].cells[i]
    c.text = ""
    add_runs(c.paragraphs[0], f"**{h}**", 11, RGBColor(0xFF, 0xFF, 0xFF))
    shade(c, "0B2E4F")
for nm, roll in [("Saurav Singh", "S20230010219"), ("Rohan Dubey", "S20230010207"), ("Ujjawal", "S20230010245"), ("Aditya Raj", "S20230030364")]:
    cells = t.add_row().cells
    cells[0].text = nm
    cells[1].text = roll
for row in t.rows:
    row.cells[0].width = Cm(6)
    row.cells[1].width = Cm(5)
for _ in range(6):
    doc.add_paragraph()
P("Demo application: CryptoVault (MongoDB · Express · React · Node.js)", "c", 10, color=GREY)
P("November 2026", "c", 10, color=GREY)
page_break()

# ================================================================== ABSTRACT + TOC
H("Abstract", 1)
P(
    "Hybrid cryptography protects files stored in the cloud by combining a fast symmetric cipher for the data with public-key cryptography for the key. "
    "We studied the Hybrid AES-ECC model of Rehman et al. (Electronics 10(21):2673, 2021), which claims a secure and optimized scheme for sharing data over the cloud "
    "that ensures authentication and data integrity. Because the authors' repository contains no code, we re-implemented the scheme from the algorithm boxes in the paper, "
    "inside a full MERN web application (CryptoVault), and attacked it."
)
P(
    f"We identify three challenges. **C1:** the AES key is derived from the ECC _public_ key, so anyone can decrypt; our attacker recovered {e1['base_recovered']}/{e1['files']} files using only public information. "
    f"**C2:** there is no integrity or authentication mechanism and the cipher is used in an ECB-like way; {B2} of {T2:,} tampering attempts were detected and "
    f"{e3['base']['repeated_block_pct']:.1f}% of the 16-byte blocks of an encrypted image repeated. **C3:** the cloud provider performs encryption (it sees plaintext), "
    "sharing is only an access list, and revocation is impossible; the paper's evaluation also has methodological errors."
)
P(
    "We propose an **Authenticated Hybrid Envelope (AHE)**: a fresh 256-bit random data key per file, AES-256-GCM with chunk-bound associated data, "
    "ECIES-style ECDH (P-256) + HKDF key wrapping for every recipient, ECDSA (P-256/SHA-256) signatures over a manifest, client-side (end-to-end) encryption with password-sealed private keys, "
    f"and revocation by re-keying. Under the same experiments the attacker recovers {e1['proposed_recovered']}/{e1['files']} files, {100 * P2 / T2:.0f}% of tampering is detected, and the ciphertext reaches "
    f"{e3['proposed']['entropy_bits_per_byte']:.2f} bits/byte of Shannon entropy with no repeated blocks. The cost is roughly {perf[1]['proposed_enc_ms']:.0f} ms per file plus "
    f"about {perf[16384]['proposed_enc_mbps']:.0f} MB/s throughput on large files. All parts of the solution come from the course syllabus "
    "(AES and modes of operation, ECC and Diffie-Hellman, hash functions and digital signatures, Shannon entropy, key management)."
)
P("**Keywords:** cloud storage, hybrid cryptography, AES-GCM, ECC, ECDH, ECDSA, authenticated encryption, key management, Shannon entropy.", "l")
H("Contents", 1)
tocp = doc.add_paragraph()
field(tocp, 'TOC \\o "1-2" \\h \\z \\u')
page_break()

# ================================================================== 1 INTRODUCTION
H("1. Introduction", 1)
H("1.1 Introduction to the topic", 2)
P(
    "Cloud storage services let users keep files on remote servers and share them with others from any device. The data owner, however, loses physical control: "
    "the files sit on infrastructure run by a third party and are reachable by its administrators, its backups and, after a breach, by outsiders. "
    "Cryptography is the only protection that does not depend on trusting the provider."
)
P(
    "In practice such systems use **hybrid cryptography**. A symmetric cipher such as AES encrypts the (large) file because it is fast, and a public-key algorithm such as RSA or ECC "
    "protects or distributes the symmetric key, because public-key cryptography solves the key-distribution problem. The same pattern is used in TLS, PGP and S/MIME."
)
H("1.2 Background and motivation", 2)
P(
    "Many papers propose hybrid schemes for cloud storage, and they are usually evaluated mainly on speed (encryption time, key size, power). Speed means little if the construction "
    "is insecure: a scheme can use strong primitives (AES, ECC) and still fail because of how they are combined, for example in how keys are derived, which mode of operation is used, "
    "or who holds the keys. Our motivation was therefore to take one well-cited published scheme, rebuild it exactly, and **attack** it rather than only time it."
)
H("1.3 Importance in cyber security", 2)
P(
    "File sharing must provide the classic security goals: **confidentiality** (only intended users read the file), **integrity** (no undetected modification), "
    "**authentication** (the file really comes from the claimed owner), and correct **access control and revocation**. Integrity matters as much as secrecy. "
    "A silently modified payment order, contract or medical record is as harmful as a leaked one. These goals are the course objectives (confidentiality, integrity, authentication, non-repudiation)."
)
H("1.4 Problem statement", 2)
P(
    "_Does the published Hybrid AES-ECC model (Rehman et al., 2021) actually keep shared cloud files confidential and unmodified against a curious or malicious cloud and outsiders who obtain "
    "the stored data? If not, how can it be fixed, using standard primitives from the course, without making it impractically slow?_"
)
H("1.5 Objectives", 2)
numbered(
    [
        "Re-implement the base scheme faithfully from the paper (its published repository contains no code).",
        "Identify at least three challenges/limitations, and demonstrate each with a working attack or measurement.",
        "Design an improved scheme that solves at least one challenge. We address all three.",
        "Implement both schemes in a working MERN application whose interface shows every cryptographic step live (for the demonstration).",
        "Evaluate both schemes with the same security and performance experiments and compare them.",
    ]
)
H("1.6 Threat model and assumptions", 2)
bullets(
    [
        "**Cloud provider (honest-but-curious or malicious):** can read everything it stores, can modify, delete, reorder or swap stored bytes, and can serve them to anyone.",
        "**Outsider with a leaked copy:** obtains the stored ciphertext and metadata, e.g. from a misconfigured bucket or a stolen backup, and can read the public-key directory.",
        "**Revoked user:** previously had access and must not be able to read versions created after revocation.",
        "**Assumptions:** the users' own devices/browsers are not compromised, transport is protected by TLS, and users can compare public-key fingerprints out-of-band when needed.",
    ]
)
H("1.7 Mapping to the course syllabus", 2)
table(
    ["Course unit / module", "Concept", "Where it is used in this project"],
    [
        ["Unit 1 – Number theory", "Modular arithmetic, inverses, primes", "Prime-field arithmetic behind ECC point operations and ECDSA (k⁻¹ mod n)"],
        ["Unit 2 – Shannon's theory", "Entropy, key equivocation, perfect secrecy", "C1 analysis H(K | public key) = 0; ciphertext entropy metric; password entropy meter"],
        ["Module 3 – Symmetric crypto", "AES, finite fields, modes (ECB, CBC, CTR)", "Base AES-ECB; proposed AES-256-GCM (CTR + GHASH in GF(2¹²⁸)); ECB leakage"],
        ["Module 4 – Public-key crypto", "ECC (and RSA for comparison)", "P-256 key pairs; ECC vs RSA key size and speed"],
        ["Module 5 – Hash & signatures", "SHA family, DSA / digital signatures", "SHA-256 of ciphertext, HKDF, ECDSA-signed manifest"],
        ["Unit 6 – Applications", "Diffie-Hellman, key distribution and management", "ECDH key wrapping per recipient, sharing, revocation by re-keying"],
    ],
    widths=[3.8, 4.4, 8.2],
    caption_txt="Course topics used in the project.",
)

# ================================================================== 2 OVERVIEW OF EXISTING ARTICLE
H("2. Overview of the Existing Article", 1)
H("2.1 The selected article", 2)
P(
    "S. Rehman, N. T. Bajwa, M. A. Shah, A. O. Aseeri and A. Anjum, “Hybrid AES-ECC Model for the Security of Data over Cloud Storage”, _Electronics_, vol. 10, no. 21, art. 2673, 2021 "
    "(MDPI, open access, peer reviewed), DOI 10.3390/electronics10212673. The paper argues that a single algorithm is either slow or insecure, and proposes combining ECC and AES "
    "“to ensure authentication and data integrity” for data shared over cloud storage “without involving a third party”."
)
P("The paper lists three contributions:")
bullets(
    [
        "A hybrid model where the key used by AES is generated with the help of ECC, so that the key size is reduced.",
        "Reduced computational power and memory compared with existing symmetric/asymmetric schemes.",
        "An algorithm describing how the public key is generated with ECC and how encryption/decryption is done with AES.",
    ]
)
H("2.2 Technologies used in the paper", 2)
H("2.2.1 Advanced Encryption Standard (AES)", 3)
P(
    "AES (FIPS-197) is a symmetric block cipher with a 128-bit block and 128-, 192- or 256-bit keys (10, 12 or 14 rounds). Each round applies **SubBytes** (a non-linear S-box built from "
    "inversion in GF(2⁸)), **ShiftRows**, **MixColumns** (a linear mix over GF(2⁸)) and **AddRoundKey** (XOR with a round key from the key expansion). "
    "The same key encrypts and decrypts, so AES is fast but needs a way to share the key. "
    "A block cipher needs a **mode of operation** for data longer than one block. In ECB every block is encrypted independently. CBC and CTR use an IV or a nonce so that equal blocks produce different ciphertext."
)
H("2.2.2 Elliptic Curve Cryptography (ECC)", 3)
P(
    "ECC works with the points of a curve y² = x³ + ax + b over a prime field F_p. Points can be added (chord-and-tangent rule), and repeated addition gives scalar multiplication. "
    "A private key is a random integer n and the public key is the point **P = n·G** for a fixed base point G. Computing n from P is the **elliptic-curve discrete logarithm problem (ECDLP)**, "
    "which has no known efficient solution. ECC therefore offers the same security as RSA with much smaller keys: NIST SP 800-57 equates 256-bit ECC with 3072-bit RSA "
    "(128-bit security), 384-bit ECC with 7680-bit RSA and 512-bit ECC with 15360-bit RSA."
)
H("2.3 Working methodology of the base scheme", 2)
P("The algorithm is given in two boxes of the paper (Section 4.3), and the architecture in Figures 3 and 5:")
bullets(
    [
        "**Box 1 – public key generation:** select a prime n, select a private number n(a) < n, compute a curve point G, and return the public key **P = n(a) · G**.",
        "**Box 2 – encryption/decryption:** take the input file; “add the key generated by ECC which is the public key”; perform AES encryption “on the input file by using the public key which is generated by ECC”; "
        "upload; to decrypt, the file is “translated by using the public key given by ECC”.",
        "**Architecture (Fig. 3/5):** the user's request goes to the Cloud Service Provider (CSP), which performs “verification” and then encryption (or decryption) before storing to (or returning from) the cloud server.",
    ]
)
figure(f"{FIG}/fig_base_flow.png", 15.5, "Base scheme as described in the paper (our rendering). The AES key is a function of the public key P only.")
H("2.4 Results reported by the paper", 2)
P(
    "The paper evaluates encryption and decryption time on text data with key sizes of 64, 128, 192 and 256 bits (Python, Intel i7-8550U). It reports that the hybrid model is the fastest, "
    "and also reports the avalanche effect, key sizes compared with RSA, and power consumption."
)
figure(f"{FIG}/fig_paper_results.png", 13.5, "Encryption time reported in the paper (Table 7 of the paper), re-plotted.")
table(
    ["Metric (paper)", "Hybrid AES-ECC", "AES", "DES", "Blowfish"],
    [
        ["Encryption time, 64–256-bit keys (s)", "2.40 – 2.60", "3.42 – 3.60", "3.89 – 4.34", "4.31 – 4.70"],
        ["Decryption time, 64–256-bit keys (s)", "1.64 – 2.10", "2.69 – 3.08", "3.11 – 3.58", "3.89 – 4.25"],
        ["Avalanche, 1-bit key / plaintext change", "0.61 / 0.64", "0.51 / 0.55", "–", "0.29 / 0.18"],
        ["Key size claim (Table 5)", "ECC 256 ≈ RSA 3024 (1:12)", "", "", ""],
    ],
    widths=[5.6, 3.2, 2.4, 2.4, 2.4],
    caption_txt="Main results reported by Rehman et al. (2021).",
)
H("2.5 Advantages and applications", 2)
bullets(
    [
        "Simple design that is easy to implement: one ECC key pair per user and one AES encryption per file.",
        "ECC gives small keys and fast key generation, which suits mobile and IoT clients.",
        "Applications suggested by the paper: cloud storage for personal data, organisational documents and data accessed from weakly secured devices.",
    ]
)

# ================================================================== 3 IMPLEMENTATION OF EXISTING APPROACH
H("3. Implementation of the Existing Approach", 1)
H("3.1 Tools, technologies and languages", 2)
table(
    ["Layer", "Technology", "Purpose"],
    [
        ["Crypto (base scheme)", f"Node.js {meta['node']} `crypto` (OpenSSL {meta['openssl']})", "P-256 key generation, SHA-256, AES-128-ECB/CBC"],
        ["Crypto (proposed)", "W3C Web Crypto API (browser and Node.js)", "AES-GCM, ECDH, ECDSA, HKDF, PBKDF2, SHA-256"],
        ["Server", "Express 4, Mongoose 8, Multer, JWT, bcrypt", "REST API, file upload, authentication, Attack Lab, live log (SSE)"],
        ["Database", "MongoDB 7 with GridFS", "users, file metadata/manifests, ciphertext blobs"],
        ["Client", "React 18, React Router, Recharts, Vite 7", "UI, client-side encryption, Crypto Inspector, charts"],
        ["Testing / analysis", "node:test, Playwright, Python (matplotlib)", "unit tests, end-to-end UI test + screenshots, figures"],
    ],
    widths=[3.6, 6.2, 6.6],
    caption_txt="Tools and technologies.",
)
H("3.2 Implementation methodology", 2)
P(
    "The repository linked in the paper (github.com/sabarehmanciit/Hybrid-AES-ECC-Model) contains only a README, so we implemented the boxes ourselves. Where the paper is silent, we "
    "chose the most charitable concrete option, so that every weakness we report is in the design and not in our choices:"
)
table(
    ["Not specified in the paper", "Our choice", "Reason"],
    [
        ["Elliptic curve", "NIST P-256 (prime256v1)", "standard 128-bit-security curve"],
        ["How the AES key is obtained from the ECC public key", "K = SHA-256(x-coordinate of P), truncated to 128 bits", "a proper hash. Any deterministic function of P has the same flaw"],
        ["AES mode, IV, padding", "AES-128-ECB with PKCS#7 (variant: CBC with fixed IV)", "Box 2 mentions no IV or nonce and nothing is stored with the file"],
        ["Where encryption happens", "On the server (CSP) after login verification", "as in the paper's Figures 3 and 5"],
    ],
    widths=[5.2, 5.6, 5.6],
    caption_txt="Implementation decisions for details the paper leaves open.",
)
code(
    [
        "// crypto-core/src/base_aes_ecc.js  (excerpt)",
        "export function baseKeygen() {                       // Box 1: P = n(a)·G",
        "  const ecdh = crypto.createECDH('prime256v1'); ecdh.generateKeys();",
        "  return { priv: ecdh.getPrivateKey(), pub: ecdh.getPublicKey(null, 'uncompressed') };",
        "}",
        "export function deriveAesKeyFromPublic(pub, bits = 128) {   // Box 2: key from PUBLIC key",
        "  return sha256(pub.subarray(1, 33)).subarray(0, bits / 8);",
        "}",
        "export function baseEncrypt(plain, pub) {",
        "  const c = crypto.createCipheriv('aes-128-ecb', deriveAesKeyFromPublic(pub), null);",
        "  return Buffer.concat([c.update(plain), c.final()]);",
        "}",
    ]
)
H("3.3 Experimental setup", 2)
bullets(
    [
        f"Machine: {meta['cpu']} ({meta['cores']} cores), {meta['platform']}; Node.js {meta['node']} with OpenSSL {meta['openssl']}.",
        "Data: synthetic employee/payment records (1–65 KiB, text with repeated structure), random binary files, a 512×384 flat-colour image (BMP, 589,824 pixel bytes), and a 96-byte payment order.",
        "Performance: file sizes from 1 KiB to 32 MiB; median of 7–25 repetitions after a warm-up run, with garbage collection forced between runs.",
        "All experiments are in `app/bench/run.js` and use exactly the code that the web application uses. Results are written to `results.json`, which the slides and this report read.",
    ]
)
H("3.4 Results of the implementation", 2)
P(
    f"The base scheme works end-to-end in our application: all {e1['files']} test files encrypt and decrypt correctly. Our implementation confirms the paper's efficiency argument for ECC: "
    f"generating a P-256 key pair takes {e9['p256_keygen_ms']:.2f} ms, against {e9['rsa3072_keygen_ms']:.0f} ms for RSA-3072 at the same security level, and AES-128 encrypts a 16 MiB file in "
    f"{perf[16384]['base_enc_ms']:.1f} ms (≈{perf[16384]['base_enc_mbps']:.0f} MB/s). We cannot reproduce the paper's absolute timings in seconds, because its data set and code are not available."
)
figure(f"{SHOT}/02_upload_base.png", 16, "Uploading a file with the base scheme in CryptoVault. The Crypto Inspector (right) shows the CSP receiving the plaintext and deriving the AES key from the public key.")

# ================================================================== 4 CHALLENGES
H("4. Challenges and Limitations", 1)
P("We identified three challenges. Each one was demonstrated with a working attack in the Attack Lab of our application and measured in the experiment harness.")
H("4.1 Challenge C1 – The AES key is derived from the public key", 2)
P(
    "**What is wrong.** Box 2 uses the ECC public key as the source of the AES key (“AES encryption is performed on the input file by using the public key which is generated by ECC”). "
    "A public key is published by design; the paper itself states that “the public key is known by every person”. Anyone who obtains the ciphertext can therefore recompute the AES key and decrypt. "
    "The ECC private key n(a) is never used, so the hardness of the ECDLP gives no protection."
)
P(
    "**Why it is important (course link).** Kerckhoffs' principle says that a system must stay secure when everything except the key is public. Here the key itself is public. "
    "In Shannon's terms, the **key equivocation** H(K | P) is 0 bits: after seeing the public key, the attacker has no uncertainty about the AES key. "
    "No choice of cipher (AES-128 or AES-256) can compensate for a key with zero entropy."
)
P(
    f"**Evidence.** Attack 1 gives an attacker only the stored ciphertext and the owner's public key from the directory. It recovered **{e1['base_recovered']} of {e1['files']} files** (Section 7.2)."
)
H("4.2 Challenge C2 – No integrity or authentication; ECB-style encryption", 2)
P(
    "**What is wrong.** The abstract claims the scheme ensures “authentication and data integrity”, but the algorithm contains no MAC, no hash, no signature and no authenticated mode. "
    "AES is used without an IV, so the same plaintext block always gives the same ciphertext block, which is ECB behaviour. Three consequences follow:"
)
bullets(
    [
        "**Malleability:** the cloud can flip bits, delete blocks, swap blocks or splice blocks from another file, and decryption still succeeds. In the payment-order demo, swapping two ciphertext blocks swaps the amounts of Alice and Mallory.",
        "**Pattern leakage:** equal plaintext blocks give equal ciphertext blocks, so the shapes in an image stay visible after encryption.",
        "**Deterministic encryption:** uploading the same file twice gives identical ciphertexts, which tells an observer that two files are equal.",
    ]
)
P(
    f"**Evidence.** {B2} of {T2:,} tampering attempts were detected, and {BS2:,} produced silently corrupted output. {e3['base']['repeated_block_pct']:.1f}% of the image's ciphertext blocks are repeats "
    "(Section 7.3–7.4)."
)
H("4.3 Challenge C3 – No real sharing, revocation or fair evaluation", 2)
P(
    "**What is wrong.** Encryption is done by the CSP (Figures 3 and 5), so the provider receives the plaintext and can compute the key. This contradicts the stated goal of working “without involving a third party”. "
    "Sharing can only be an access-control list on the server: there are no per-user keys, so removing a user changes no key and **revocation is impossible** cryptographically. "
    "A user who was once allowed, or anyone else, can still decrypt any copy with the public key."
)
P("**Evaluation issues.** The paper's evaluation also has methodological problems that make its comparisons unreliable:")
bullets(
    [
        "AES is reported with a “64-bit key”, but FIPS-197 defines AES only for 128-, 192- and 256-bit keys.",
        "Table 5 lists RSA equivalents of 3024, 7068 and 16360 bits; NIST SP 800-57 gives 3072, 7680 and 15360 bits.",
        "An avalanche effect above 50% (61–64%) is read as “more secure”. The strict avalanche criterion (Webster & Tavares) asks for 50%; any deviation in either direction indicates bias.",
        "The “power consumption (W)” values in Tables 10 and 11 are identical to the encryption and decryption times in Tables 7 and 8, which suggests power was not measured separately.",
        "The hybrid model (AES plus ECC operations) is reported to be faster than AES alone, which is only possible if different implementations were compared.",
        "The linked code repository contains only a README, so the results cannot be reproduced.",
    ]
)
table(
    ["#", "Challenge", "Affects", "Impact"],
    [
        ["C1", "AES key derived from public ECC key", "Confidentiality", "Any outsider or insider decrypts every file. Security reduces to zero."],
        ["C2", "No MAC/signature; ECB-style mode", "Integrity, authentication, confidentiality", "Silent tampering (financial/medical data), pattern and equality leakage"],
        ["C3", "CSP encrypts; no per-user keys; flawed evaluation", "Key management, usability, scalability", "No revocation, provider must be fully trusted, misleading performance claims"],
    ],
    widths=[1.0, 5.0, 3.8, 6.6],
    caption_txt="Summary of the challenges.",
)

# ================================================================== 5 PROPOSED APPROACH
H("5. Proposed Approach: Authenticated Hybrid Envelope (AHE)", 1)
H("5.1 Selected challenges", 2)
P(
    "The guidelines ask for at least one challenge to be solved. AHE solves **C1** and **C2** completely and solves the cryptographic part of **C3** (end-to-end encryption, per-user sharing, revocation). "
    "The evaluation issues of C3 are addressed by our own measurement methodology (Section 6.3)."
)
H("5.2 Design principles", 2)
numbered(
    [
        "**Never derive a secret from public data.** Every file gets a fresh random 256-bit data-encryption key (DEK).",
        "**Encrypt and authenticate together.** Use an AEAD mode (AES-GCM) so that any change to the ciphertext is detected (Bellare & Namprempre).",
        "**Encrypt the key separately for each recipient** with Diffie-Hellman on the curve (ECIES-style key encapsulation).",
        "**Sign what you upload.** The owner signs a manifest that binds the ciphertext hash, the recipients' wrapped keys and the version.",
        "**Encrypt at the edge.** All cryptography runs in the users' browsers; the server stores only opaque bytes (zero-knowledge server).",
    ]
)
H("5.3 Building blocks", 2)
bullets(
    [
        "**DEK:** 32 bytes from the browser's CSPRNG (`crypto.getRandomValues`). The key has 256 bits of entropy and is never stored in plaintext.",
        "**AES-256-GCM:** the file is split into 1 MiB chunks. Nonce = 64-bit random prefix ∥ 32-bit chunk counter. The associated data binds `scheme | fileId | version | chunk index | last-chunk flag`, "
        "which prevents reordering, truncation and splicing between files or versions. GCM = CTR mode for secrecy + GHASH (multiplication in GF(2¹²⁸)) for the 128-bit tag.",
        "**Key wrapping (ECDH + HKDF):** for recipient j with public key Q_j the sender picks an ephemeral r, sends R = r·G, computes S = r·Q_j, and derives KEK = HKDF-SHA256(S, salt = fileId, info = context ∥ R). "
        "The DEK is encrypted with AES-GCM under KEK. The recipient computes the same S = d_j·R with its private key d_j. This is the Diffie-Hellman exchange from Unit 6, performed on elliptic curves.",
        "**Signature:** ECDSA over P-256 with SHA-256 on the canonical JSON manifest {fileId, version, size, chunks, nonce prefix, encrypted name, SHA-256(ciphertext), recipients' wrapped keys}.",
        "**Key vault:** each user's ECDH and ECDSA private keys are encrypted in the browser with AES-GCM under PBKDF2-SHA256(password, random salt, 600,000 iterations). The login token is a different PBKDF2 output, "
        "and the server stores only bcrypt(token), so it never learns the password and cannot open the vault.",
    ]
)
figure(f"{FIG}/fig_proposed_flow.png", 15.5, "Proposed AHE scheme: upload (top row), per-recipient key wrapping and recipient-side verification/decryption.")
H("5.4 Algorithms (pseudocode)", 2)
code(
    [
        "Algorithm 1  UPLOAD(file, recipients, owner)",
        "  DEK ← CSPRNG(256 bit);  prefix ← CSPRNG(64 bit)",
        "  for i, chunk in split(file, 1 MiB):",
        "      C_i ← AES-GCM_DEK(nonce = prefix‖i, AAD = fileId‖version‖i‖last, chunk)",
        "  for each recipient j (incl. owner):",
        "      r ← random; R ← r·G; S ← r·Q_j; KEK ← HKDF(S, fileId, ctx‖R)",
        "      wrap_j ← AES-GCM_KEK(DEK)",
        "  M ← {fileId, version, size, prefix, Enc(name), SHA-256(C), [wrap_j, R_j]}",
        "  σ ← ECDSA_sign(sk_owner, M);  erase DEK;  send (C, M, σ) to cloud",
        "",
        "Algorithm 2  OPEN(C, M, σ, user j)",
        "  if not ECDSA_verify(pk_owner, M, σ)        → BLOCK (manifest changed)",
        "  if SHA-256(C) ≠ M.ctHash                   → BLOCK (ciphertext changed)",
        "  if no wrap for j                           → DENY  (not a recipient / revoked)",
        "  S ← d_j·R_j;  DEK ← AES-GCM-Dec_KEK(wrap_j)  (tag check)",
        "  for each chunk: P_i ← AES-GCM-Dec_DEK(C_i)  (tag check, else BLOCK)",
        "",
        "Algorithm 3  SHARE(M, new user k):  DEK ← unwrap(own entry); add wrap_k; re-sign M",
        "Algorithm 4  REVOKE(user k):  P ← OPEN(...); UPLOAD(P, recipients \\ {k}) as version+1",
    ]
)
H("5.5 Security analysis (informal)", 2)
bullets(
    [
        "**C1 fixed.** The attacker sees C, M, σ and every public key. Obtaining the DEK requires either S = r·Q_j = d_j·R, which is the elliptic-curve Diffie-Hellman problem, or a brute-force search over 2²⁵⁶ keys. "
        "The DEK is independent of all public values, so H(DEK | public data) = 256 bits instead of 0.",
        "**C2 fixed.** Changing any ciphertext byte changes SHA-256(C) and the GCM tag of that chunk. Changing the manifest invalidates the ECDSA signature, and creating a new valid signature requires the owner's private key (EUF-CMA security of ECDSA). "
        "A random fresh nonce and DEK per upload make encryption non-deterministic, so equal files and equal blocks give unrelated ciphertexts.",
        "**C3 fixed (cryptographic part).** The server never receives plaintext, a DEK or a private key. A new user receives one extra wrapped key, without re-encryption. Revocation re-encrypts under a new DEK, "
        "and because the version is bound into the associated data, a revoked user's old wrapped key cannot be re-used on the new version.",
    ]
)
H("5.6 Limitations of the proposed approach", 2)
bullets(
    [
        "**Public-key substitution:** a malicious server could hand out a fake public key. We display SHA-256 key fingerprints for out-of-band comparison; a key-transparency log would be the stronger fix.",
        "**Metadata:** file sizes, upload times, access patterns and the number of recipients remain visible to the server.",
        "**Already-downloaded data:** revocation protects new versions only; a user can keep a copy of what they already decrypted (true for any system).",
        "**Rollback:** the server could serve an older, validly signed version; clients would need to remember the highest version they have seen.",
        "**No post-quantum security:** ECDH and ECDSA can be broken by a large quantum computer; ML-KEM (FIPS 203) would replace ECDH in a future version.",
    ]
)

# ================================================================== 6 IMPLEMENTATION OF PROPOSED
H("6. Implementation of the Proposed Approach", 1)
H("6.1 Implementation process and code structure", 2)
P(
    "The cryptography lives in one shared module, `crypto-core`. The **same file** runs in the React client (browser WebCrypto) and in Node.js (seed script, tests, benchmarks), so the benchmarked code is the demonstrated code. "
    "Every function accepts an optional `trace` callback. The client's **Crypto Inspector** panel shows each step with its real values (keys, nonces, shared secrets, tags, hashes, signatures) "
    "and can play them back one at a time for the demonstration."
)
table(
    ["Path", "Content"],
    [
        ["`app/crypto-core/src/base_aes_ecc.js`", "Base scheme (Box 1 + Box 2), traced versions for the CSP"],
        ["`app/crypto-core/src/proposed_ahe.js`", "AHE: key generation, vault, wrap/unwrap, encrypt/decrypt, share, re-key, attack helper"],
        ["`app/crypto-core/src/analysis.js`", "Shannon entropy, repeated-block ratio, chi-square, bit difference (avalanche)"],
        ["`app/server/src/routes/*.js`", "auth (PBKDF2 token + bcrypt + JWT), files (base & proposed), lab (attacks), SSE live log"],
        ["`app/client/src/pages/*.jsx`", "Files, Attack Lab, What the Cloud Sees, Results; `components/Inspector.jsx`"],
        ["`app/bench/run.js`", "Experiments E1–E9 (security + performance)"],
        ["`app/crypto-core/test/crypto.test.js`", "Unit tests: round trip, tamper detection, attacks, sharing, revocation, vault"],
    ],
    widths=[6.6, 9.8],
    caption_txt="Main modules of the implementation.",
)
figure(f"{FIG}/fig_architecture.png", 15.5, "Architecture of the CryptoVault demonstration application.")
H("6.2 Application walk-through", 2)
figure(f"{SHOT}/03_upload_proposed.png", 16, "Upload with the proposed scheme. The Inspector shows the browser generating the DEK, encrypting with AES-GCM, locking the key for each recipient with ECDH, and signing; the server reports that it received only high-entropy ciphertext.")
figure(f"{SHOT}/08_cloud_view.png", 16, "“What the Cloud Sees”: the raw MongoDB/GridFS contents. Base files expose their names and have keys derivable from public keys; proposed files expose neither.")
H("6.3 Experimental setup (security and performance)", 2)
table(
    ["Exp.", "What is measured", "Trials / sizes"],
    [
        ["E1", "Decryption by an attacker who knows only public data", f"{e1['files']} files (1–65 KiB)"],
        ["E2", "Detection of 5 tampering types (bit flip, block swap, block delete, splice, file swap / manifest edit)", f"{list(e2.values())[0]['trials']} per type, {T2:,} total"],
        ["E3", "Pattern leakage on an image: entropy, repeated blocks, chi-square", "512×384 image"],
        ["E4", "Determinism: same file encrypted twice", "4 KiB document"],
        ["E5", "Avalanche: 1-bit key / plaintext change (block and whole file)", f"{e5['trials']} trials"],
        ["E6", "Encryption/decryption time and throughput", "1 KiB – 32 MiB"],
        ["E7", "Sharing cost vs number of recipients; adding a recipient later", "1–100 recipients, 1 MiB"],
        ["E8", "Revocation (re-key) cost", "64 KiB – 16 MiB"],
        ["E9", "Cost of primitives (P-256 vs RSA-3072)", "50–100 runs"],
    ],
    widths=[1.3, 10.3, 4.8],
    caption_txt="Experiments (all in app/bench/run.js).",
)

# ================================================================== 7 RESULTS
H("7. Results and Analysis", 1)
H("7.1 Summary", 2)
table(
    ["Test", "Base AES-ECC", "Proposed AHE"],
    [
        [f"Files decrypted using only public data (E1)", f"{e1['base_recovered']} / {e1['files']}", f"{e1['proposed_recovered']} / {e1['files']}"],
        [f"Tampering detected (E2, {T2:,} attacks)", f"{100 * B2 / T2:.1f} %", f"{100 * P2 / T2:.0f} %"],
        ["Repeated 16-byte blocks in encrypted image (E3)", f"{e3['base']['repeated_block_pct']:.2f} %", f"{e3['proposed']['repeated_block_pct']:.0f} %"],
        ["Ciphertext entropy, bits/byte (E3)", f"{e3['base']['entropy_bits_per_byte']:.3f}", f"{e3['proposed']['entropy_bits_per_byte']:.4f}"],
        ["Chi-square vs uniform, 255 d.o.f. (E3)", f"{e3['base']['chi_square']:,.0f}", f"{e3['proposed']['chi_square']:.0f}"],
        ["Same file twice: bits that differ (E4)", f"{e4['base_bit_difference_pct']:.0f} % (identical)", f"{e4['proposed_bit_difference_pct']:.2f} %"],
        ["1-bit plaintext change, whole 4 KiB file (E5)", f"{e5['whole_file_4KiB_base_pct']:.2f} %", f"{e5['whole_file_4KiB_proposed_pct']:.2f} %"],
        ["Revocation of a user (E8)", "impossible", f"{rev[1024]['rekey_ms']:.1f} ms per MiB"],
        ["Encrypt 1 MiB / 16 MiB (E6)", f"{perf[1024]['base_enc_ms']:.2f} / {perf[16384]['base_enc_ms']:.1f} ms", f"{perf[1024]['proposed_enc_ms']:.2f} / {perf[16384]['proposed_enc_ms']:.1f} ms"],
    ],
    widths=[7.6, 4.4, 4.4],
    caption_txt="Base vs. proposed scheme under identical experiments.",
)
H("7.2 Attack 1: decryption with public information (C1)", 2)
P(
    f"With only the stored ciphertext and the owner's public key, the attacker decrypted **all {e1['base_recovered']} base files**. Against the proposed scheme the same attacker, given the ciphertext, the full manifest and "
    f"every public key in the directory, tried {e1['proposed_candidate_keys_tried']:,} candidate keys derived from all public values, and **none** passed the GCM tag check."
)
figure(f"{SHOT}/05_attack1_public_key.png", 16, "Attack Lab, attack 1: the base file is fully recovered from public data, while every key candidate fails against the proposed file. The steps appear in the Inspector.")
H("7.3 Attack 2: tampering by the cloud (C2)", 2)
P(
    f"The base scheme raised no error for any of the {T2:,} modifications. In {BS2:,} cases it returned corrupted plaintext as if it were valid. In the remaining cases the modification happened to leave the output unchanged, "
    "e.g. two identical ECB blocks were swapped, which is itself a symptom of ECB. The proposed scheme detected **every** modification, through the ECDSA signature, the SHA-256 ciphertext hash or the GCM tag, and released no data."
)
figure(f"{FIG}/fig_tamper.png", 14.5, "Tampering detection rate per attack type.")
figure(f"{SHOT}/06_attack2_tamper.png", 16, "Payment-order demo: swapping ciphertext blocks 2 and 4 swaps the amounts of Alice and Mallory under the base scheme without any warning; the proposed scheme blocks the file.")
H("7.4 Pattern leakage, entropy and determinism", 2)
P(
    f"Encrypting the flat-colour image with the base scheme leaves the picture recognisable (Figure below). Its ciphertext entropy is only {e3['base']['entropy_bits_per_byte']:.2f} bits/byte, and "
    f"{e3['base']['repeated_block_pct']:.1f}% of its blocks are repeats, exactly as many as in the plaintext. The proposed ciphertext reaches {e3['proposed']['entropy_bits_per_byte']:.4f} bits/byte "
    f"(the maximum is 8) with no repeated block, and its chi-square statistic ({e3['proposed']['chi_square']:.0f}) is in the range expected for uniformly random bytes (≈255). "
    f"Uploading the same document twice gives byte-identical ciphertexts in the base scheme, and ciphertexts that differ in {e4['proposed_bit_difference_pct']:.1f}% of their bits in the proposed scheme."
)
figure(f"{FIG}/fig_ecb.png", 15.5, "The same image encrypted by both schemes.")
H("7.5 Avalanche effect re-evaluated", 2)
P(
    f"Measured correctly, AES changes {e5['aes_block_1bit_key_change_pct']:.2f}% of ciphertext bits for a 1-bit key change and {e5['aes_block_1bit_plaintext_change_pct']:.2f}% for a 1-bit plaintext change: "
    "essentially the ideal 50%. The paper's figures of 61–64% for its hybrid model are therefore not “more secure”; they indicate a measurement problem. At the level of a whole file, "
    f"a 1-bit change alters only {e5['whole_file_4KiB_base_pct']:.2f}% of the base ciphertext (one ECB block), compared with {e5['whole_file_4KiB_proposed_pct']:.2f}% for the proposed scheme, which re-encrypts with a fresh key and nonce."
)
figure(f"{FIG}/fig_entropy_avalanche.png", 15.5, "Left: entropy and repeated blocks of the encrypted image. Right: avalanche measurements (dashed line = ideal 50%).")
H("7.6 Performance", 2)
P(
    f"The proposed scheme has a fixed cost of about {perf[1]['proposed_enc_ms']:.1f} ms per file for encryption and {perf[1]['proposed_dec_ms']:.1f} ms for decryption, made up of two ECDH key wraps (owner + one recipient), "
    f"one ECDSA signature and the key imports (one P-256 operation costs ≈{e9['p256_ecdh_ms']:.2f} ms). Per byte, it adds the GCM tag computation and a SHA-256 over the ciphertext. "
    f"For a 16 MiB file encryption takes {perf[16384]['proposed_enc_ms']:.1f} ms instead of {perf[16384]['base_enc_ms']:.1f} ms, i.e. {perf[16384]['proposed_enc_mbps']:.0f} MB/s instead of {perf[16384]['base_enc_mbps']:.0f} MB/s. "
    "This is still far faster than typical network upload speeds, so users would not notice the difference. ECC is also the right choice for key wrapping: "
    f"P-256 key generation takes {e9['p256_keygen_ms']:.2f} ms against {e9['rsa3072_keygen_ms']:.0f} ms for RSA-3072."
)
figure(f"{FIG}/fig_perf.png", 15.5, "Encryption/decryption time vs file size (log-log) and encryption throughput.")
table(
    ["Size", "Base enc (ms)", "Base dec (ms)", "AHE enc (ms)", "AHE dec (ms)", "AHE enc (MB/s)"],
    [
        [
            (f"{k} KiB" if k < 1024 else f"{k // 1024} MiB"),
            f"{perf[k]['base_enc_ms']:.2f}",
            f"{perf[k]['base_dec_ms']:.2f}",
            f"{perf[k]['proposed_enc_ms']:.2f}",
            f"{perf[k]['proposed_dec_ms']:.2f}",
            f"{perf[k]['proposed_enc_mbps']:.1f}",
        ]
        for k in sorted(perf)
    ],
    widths=[2.2, 2.6, 2.6, 2.6, 2.6, 2.8],
    caption_txt="Median timings (E6).",
)
H("7.7 Sharing and revocation", 2)
P(
    f"Sharing cost grows linearly with the number of recipients (one ECDH wrap and 216 bytes of manifest each): encrypting and sharing a 1 MiB file with 100 recipients takes {e7['rows'][-1]['encrypt_and_share_ms']:.0f} ms. "
    f"Adding a recipient later needs no re-encryption and takes {e7['add_recipient_later_ms']:.1f} ms. Revocation re-encrypts the file under a new DEK: {rev[1024]['rekey_ms']:.1f} ms for 1 MiB and "
    f"{rev[16384]['rekey_ms']:.1f} ms for 16 MiB. In the application, the revoked user can still download the new ciphertext (we allow this on purpose) and is still denied, because there is no wrapped key for them in version 2. "
    "Revocation is therefore enforced by cryptography and not by the server."
)
figure(f"{FIG}/fig_share_revoke.png", 15.5, "Sharing cost vs number of recipients, and re-key (revocation) cost vs file size.")
figure(f"{SHOT}/12_bob_after_revoke.png", 16, "After revocation, Bob's browser receives version 2 but finds no wrapped key for him: access is denied by cryptography.")
H("7.8 Does the proposed approach address the challenges?", 2)
table(
    ["Challenge", "Before (base)", "After (AHE)", "Solved?"],
    [
        ["C1 key from public data", f"{e1['base_recovered']}/{e1['files']} files recovered", f"{e1['proposed_recovered']}/{e1['files']}; DEK has 256-bit entropy", "Yes"],
        ["C2 integrity / ECB", f"{100 * B2 / T2:.0f}% tampering detected; {e3['base']['repeated_block_pct']:.0f}% blocks repeat", f"{100 * P2 / T2:.0f}% detected; 0% repeat; signed uploads", "Yes"],
        ["C3 sharing / revocation", "CSP sees plaintext; no revocation", "zero-knowledge server; per-user wrap; re-key", "Yes (crypto part)"],
        ["C3 evaluation validity", "unreproducible, inconsistent tables", "open harness, medians, all numbers regenerated", "Addressed"],
    ],
    widths=[3.8, 4.6, 5.6, 2.4],
    caption_txt="Challenge-by-challenge outcome.",
)

# ================================================================== 8 CONCLUSION
H("8. Conclusion", 1)
P(
    "We re-implemented the Hybrid AES-ECC model of Rehman et al. (2021) from its published algorithm and evaluated it with real attacks instead of timing alone. The scheme is fast, but its central design "
    "decision, deriving the AES key from the ECC public key, removes all confidentiality: anyone who can read the public key can decrypt every file. It also provides none of the integrity or "
    "authentication it claims, leaks data patterns, gives the provider the plaintext, and cannot revoke users. Several of its reported results are not methodologically sound."
)
P(
    "Our Authenticated Hybrid Envelope keeps the hybrid AES + ECC idea but uses each primitive correctly: a random per-file key, AES-256-GCM for authenticated encryption, ECDH-based key wrapping for each recipient, "
    "ECDSA signatures and client-side encryption. Under identical experiments every attack failed, every tampering attempt was detected, and the ciphertext became statistically indistinguishable from random, "
    "at a cost of a few milliseconds per file. All components come from the course syllabus. The project shows that the security of a hybrid scheme depends on how the primitives are combined, "
    "not only on which primitives are used."
)
P(
    "**Future scope:** post-quantum key encapsulation (ML-KEM, FIPS 203) in a hybrid with ECDH; a key-transparency log to stop public-key substitution; client-side version tracking against rollback; "
    "and proxy re-encryption or attribute-based encryption to make revocation in very large groups cheaper."
)

# ================================================================== 9 REFERENCES
H("9. References", 1)
refs = [
    "S. Rehman, N. T. Bajwa, M. A. Shah, A. O. Aseeri, A. Anjum, “Hybrid AES-ECC Model for the Security of Data over Cloud Storage,” Electronics, vol. 10, no. 21, 2673, 2021. doi:10.3390/electronics10212673. (Base paper)",
    "NIST, FIPS PUB 197, “Advanced Encryption Standard (AES),” 2001 (updated 2023).",
    "M. Dworkin, NIST SP 800-38A, “Recommendation for Block Cipher Modes of Operation: Methods and Techniques,” 2001.",
    "M. Dworkin, NIST SP 800-38D, “Recommendation for Block Cipher Modes of Operation: Galois/Counter Mode (GCM) and GMAC,” 2007.",
    "NIST, FIPS PUB 186-5, “Digital Signature Standard (DSS),” 2023.",
    "NIST SP 800-56A Rev. 3, “Recommendation for Pair-Wise Key-Establishment Schemes Using Discrete Logarithm Cryptography,” 2018.",
    "NIST SP 800-57 Part 1 Rev. 5, “Recommendation for Key Management: Part 1 – General,” 2020.",
    "NIST, FIPS PUB 180-4, “Secure Hash Standard (SHS),” 2015.",
    "H. Krawczyk, P. Eronen, RFC 5869, “HMAC-based Extract-and-Expand Key Derivation Function (HKDF),” IETF, 2010.",
    "K. Moriarty, B. Kaliski, A. Rusch, RFC 8018, “PKCS #5: Password-Based Cryptography Specification Version 2.1,” IETF, 2017.",
    "V. Shoup, “A Proposal for an ISO Standard for Public Key Encryption (version 2.1),” IACR Cryptology ePrint Archive, Report 2001/112, 2001.",
    "M. Bellare, C. Namprempre, “Authenticated Encryption: Relations among Notions and Analysis of the Generic Composition Paradigm,” ASIACRYPT 2000, LNCS 1976, pp. 531–545.",
    "C. E. Shannon, “Communication Theory of Secrecy Systems,” Bell System Technical Journal, vol. 28, no. 4, pp. 656–715, 1949.",
    "A. Kerckhoffs, “La cryptographie militaire,” Journal des sciences militaires, vol. IX, pp. 5–38, 161–191, 1883.",
    "A. F. Webster, S. E. Tavares, “On the Design of S-Boxes,” CRYPTO '85, LNCS 218, pp. 523–534, 1986.",
    "S. Vaudenay, “Security Flaws Induced by CBC Padding – Applications to SSL, IPSEC, WTLS…,” EUROCRYPT 2002, LNCS 2332, pp. 534–545.",
    "S. Kamara, K. Lauter, “Cryptographic Cloud Storage,” Financial Cryptography Workshops 2010, LNCS 6054, pp. 136–149.",
    "W3C, “Web Cryptography API,” W3C Recommendation, 26 January 2017.",
    "NIST, FIPS PUB 203, “Module-Lattice-Based Key-Encapsulation Mechanism Standard (ML-KEM),” 2024.",
    "OWASP, “Password Storage Cheat Sheet” (PBKDF2-HMAC-SHA256, 600,000 iterations), OWASP Cheat Sheet Series, accessed 2026.",
    "D. R. Stinson, Cryptography: Theory and Practice, 3rd ed., Chapman & Hall/CRC, 2006. (Course text book)",
    "B. A. Forouzan, D. Mukhopadhyay, Cryptography and Network Security, McGraw-Hill Education, 2011. (Course text book)",
    "W. Stallings, Cryptography and Network Security: Principles and Practice, 6th ed., Pearson, 2014.",
    "MongoDB Inc., “GridFS” documentation; Node.js Foundation, “Crypto” module documentation (Node.js 22), accessed 2026.",
]
for i, r_ in enumerate(refs, 1):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.9)
    p.paragraph_format.first_line_indent = Cm(-0.9)
    p.paragraph_format.space_after = Pt(3)
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    add_runs(p, f"[{i}]  {r_}", 10)

# ================================================================== APPENDIX
H("Appendix A. Running the demonstration", 1)
P("The application needs Node.js 20.19+ and a MongoDB database (MongoDB Atlas or a local server). The connection string is read from `app/server/.env`.")
code(
    [
        "# 1. app/server/.env  (only MONGO_URI is required)",
        "MONGO_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/cryptovault",
        "",
        "# 2. install, test, run",
        "cd app",
        "npm install                 # installs server, client, crypto-core (npm workspaces)",
        "npm test                    # 5 unit tests of the crypto core",
        "npm run bench               # regenerates bench/results/results.json (~20 s)",
        "npm start                   # builds the React client and serves everything on http://localhost:5000",
        "#   demo users are created on first start: alice / Alice@Cloud2026, bob / Bob@Cloud2026, ...",
    ]
)
H("Appendix B. Division of work", 1)
table(
    ["Member", "Presentation", "Report sections", "Code / demo"],
    [
        ["Saurav Singh (S20230010219)", "Title, slide 1, conclusion", "Abstract, 1, 6, 8, Appendix A", "Server, auth & key vault, live log, Cloud View; demo part 1"],
        ["Rohan Dubey (S20230010207)", "Slides 2–3", "2, 3, 9", "Base AES-ECC scheme, Files page; demo part 2"],
        ["Ujjawal (S20230010245)", "Slide 4", "4, 7.1–7.5", "Attack Lab, analysis (entropy), experiments E1–E5; demo part 3"],
        ["Aditya Raj (S20230030364)", "Slide 5, results of slide 6", "5, 7.6–7.8", "AHE scheme, share/revoke, Results page, E6–E9; demo part 4"],
    ],
    widths=[4.2, 3.4, 3.6, 5.2],
    caption_txt="Work division (details in the separate task-division document).",
)

# footer with page numbers
for s_ in doc.sections:
    fp = s_.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = fp.add_run("Group 18 · Secure Cloud File Sharing Using Hybrid Cryptography · page ")
    r.font.size = Pt(8.5)
    r.font.color.rgb = GREY
    field(fp, "PAGE")
    for rr in fp.runs[1:]:
        rr.font.size = Pt(8.5)
s_ = doc.sections[0]
s_.different_first_page_header_footer = True

doc.save(OUT)
print("saved", OUT)
