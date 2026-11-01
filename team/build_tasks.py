"""Group 18 - task division document: one standalone brief per member (equal visible work).
usage: python3 build_tasks.py <results.json> <out.docx>"""
import json
import re
import sys

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

R = json.load(open(sys.argv[1]))
OUT = sys.argv[2]
e1 = R["e1_public_key_attack"]
e2 = R["e2_tampering"]
T2 = sum(v["trials"] for v in e2.values())
e3 = R["e3_ecb_image"]
perf = {r["size_kib"]: r for r in R["e6_performance"]}
rev = {r["size_kib"]: r for r in R["e8_revocation"]}
e7 = R["e7_sharing"]
e9 = R["e9_primitives"]

NAVY = RGBColor(0x0B, 0x2E, 0x4F)
TEAL = RGBColor(0x0E, 0x7C, 0x86)
GREY = RGBColor(0x55, 0x60, 0x70)
doc = Document()
sec = doc.sections[0]
sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
sec.left_margin = sec.right_margin = Cm(2.0)
sec.top_margin = sec.bottom_margin = Cm(1.8)
st = doc.styles["Normal"]
st.font.name = "Calibri"
st.font.size = Pt(10.5)
st.paragraph_format.space_after = Pt(4)
for lvl, size, col in [(1, 17, NAVY), (2, 12.5, TEAL), (3, 11, NAVY)]:
    h = doc.styles[f"Heading {lvl}"]
    h.font.name = "Calibri"
    h.font.size = Pt(size)
    h.font.bold = True
    h.font.color.rgb = col
    h.element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
    h.element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
    h.paragraph_format.space_before = Pt(10 if lvl > 1 else 4)
    h.paragraph_format.keep_with_next = True


def runs(p, txt, size=None, color=None):
    for part in re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", txt):
        if not part:
            continue
        if part.startswith("**"):
            r = p.add_run(part[2:-2])
            r.bold = True
        elif part.startswith("`"):
            r = p.add_run(part[1:-1])
            r.font.name = "Consolas"
            r.font.size = Pt((size or 10.5) - 1)
        else:
            r = p.add_run(part)
        if size and not part.startswith("`"):
            r.font.size = Pt(size)
        if color:
            r.font.color.rgb = color
    return p


def P(t, size=None, color=None, align=None):
    p = doc.add_paragraph()
    if align == "c":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return runs(p, t, size, color)


def B(items):
    for it in items:
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.space_after = Pt(2)
        runs(p, it)


def N(items):
    for i, it in enumerate(items, 1):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.8)
        p.paragraph_format.first_line_indent = Cm(-0.55)
        p.paragraph_format.space_after = Pt(2)
        runs(p, f"{i}.  {it}")


def shade(c, hx):
    tcPr = c._tc.get_or_add_tcPr()
    s = OxmlElement("w:shd")
    s.set(qn("w:val"), "clear")
    s.set(qn("w:color"), "auto")
    s.set(qn("w:fill"), hx)
    tcPr.append(s)


def T(header, rows, widths, size=9.5):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]
        c.text = ""
        runs(c.paragraphs[0], f"**{h}**", size, RGBColor(255, 255, 255))
        shade(c, "0B2E4F")
    for ri, row in enumerate(rows):
        cs = t.add_row().cells
        for i, v in enumerate(row):
            cs[i].text = ""
            runs(cs[i].paragraphs[0], v, size)
            if ri % 2:
                shade(cs[i], "EEF3F8")
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
        for c in row.cells:
            for p in c.paragraphs:
                p.paragraph_format.space_after = Pt(1)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def QA(qs):
    for q, a in qs:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(1)
        p.paragraph_format.keep_with_next = True
        runs(p, f"**Q. {q}**", 10.2, NAVY)
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.5)
        p.paragraph_format.space_after = Pt(5)
        runs(p, a, 10)


def brk():
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


# ================================================================== overview
P("GROUP 18  ·  CRYPTOGRAPHY PROJECT", 10, TEAL)
doc.add_heading("Task Division: Secure Cloud File Sharing Using Hybrid Cryptography", 1)
P(
    "The work is split into four **equal, self-contained roles**. Each member presents slides, runs one part of the live demo, writes report sections, owns one part of the code, "
    "and prepares one area of theory from our syllabus for the viva. Each brief below is written so that the member can work on it independently. "
    "Read your own brief fully and skim the others, so that you can answer cross-questions."
)
doc.add_heading("At a glance (equal visible work)", 2)
T(
    ["", "Saurav Singh", "Rohan Dubey", "Ujjawal", "Aditya Raj"],
    [
        ["Role", "Problem & system lead", "Base-paper lead", "Security analyst (attacks)", "Solution lead"],
        ["Slides presented", "Title, Slide 1, Conclusion (Slide 6, bottom)", "Slides 2 and 3", "Slide 4", "Slide 5, Results (Slide 6, top)"],
        ["Speaking time (slides)", "≈ 2.75 min", "≈ 3 min", "≈ 2 min", "≈ 3.5 min"],
        ["Live demo segment", "D1 App tour, login & key vault, cloud view (≈ 2.5 min)", "D2 Upload with both schemes, step by step (≈ 2.5 min)", "D3 Attack Lab: attacks 1–3 (≈ 3 min)", "D4 Share, revoke, results (≈ 2 min)"],
        ["Total speaking", "≈ 5.25 min", "≈ 5.5 min", "≈ 5 min", "≈ 5.5 min"],
        ["Report sections", "Abstract, 1, 6, 8, App. A", "2, 3, 9 (references)", "4, 7.1–7.5", "5, 7.6–7.8"],
        ["Code owned", "server/ (auth, files API, events), CloudView page", "crypto-core/base_aes_ecc.js, Dashboard (Files) page", "server/routes/lab.js, AttackLab page, analysis.js, bench E1–E5", "crypto-core/proposed_ahe.js, fileops.js, Results page, bench E6–E9"],
        ["Theory (course units)", "Unit 2 Shannon entropy & secrecy; hash/PBKDF2 basics", "Unit 1 number theory, Module 3 AES, Module 4 ECC", "Module 3 block-cipher modes; cryptanalysis; avalanche", "Unit 6 Diffie-Hellman & key mgmt; Module 5 hash & signatures; GCM"],
    ],
    [3.0, 3.6, 3.6, 3.6, 3.6],
    size=8.8,
)
doc.add_heading("Running order on presentation day (≈ 21 min)", 2)
T(
    ["#", "Part", "Who", "Time"],
    [
        ["1", "Title slide: introduce group and topic", "Saurav", "0.5 min"],
        ["2", "Slide 1: introduction, threat model, problem statement", "Saurav", "1.5 min"],
        ["3", "Slide 2: technologies (AES, ECC, hybrid model of the paper)", "Rohan", "1.5 min"],
        ["4", "Slide 3: results reported by the paper + our reproduction", "Rohan", "1.5 min"],
        ["5", "Slide 4: three weaknesses (challenges) with evidence", "Ujjawal", "2 min"],
        ["6", "Slide 5: our improvement (AHE)", "Aditya", "2 min"],
        ["7", "Slide 6 (top): results after the fix", "Aditya", "1.5 min"],
        ["8", "Slide 6 (bottom): conclusion + future work, hand over to demo", "Saurav", "0.75 min"],
        ["9", "Demo D1 → D2 → D3 → D4", "Saurav → Rohan → Ujjawal → Aditya", "10 min"],
    ],
    [0.8, 10.5, 3.6, 2.0],
)
doc.add_heading("Demo preparation (everyone, once)", 2)
N(
    [
        "Install Node.js 20.19+ (or 22 LTS). In `app/` run `npm install`, then `npm test` (5 tests must pass).",
        "Paste the MongoDB URL into `app/server/.env` (`MONGO_URI=...`). Run `npm start` and open http://localhost:5000; the console must show `[db] connected`. The demo users are created in that database on the first start.",
        "Use two browser windows: a normal one for **alice** and an incognito/private one for **bob** (each window keeps its own login). Passwords are on the login page.",
        "Before each segment, click **Clear** in the Crypto Inspector and choose **Step-by-step** mode. Click **Next ▶** to reveal one real step at a time while you explain it.",
        "Rehearse twice with the timer. If the projector is small, zoom the browser to 80–90%.",
    ]
)
brk()


# ================================================================== member template
def member(name, roll, role, goal, slides, demo, report, code, theory, viva, checklist):
    doc.add_heading(f"{name}  ({roll})", 1)
    P(f"**Role:** {role}", 11, TEAL)
    P(f"**Your task:** {goal}")
    doc.add_heading("1. Slides you present", 2)
    for title, pts in slides:
        P(f"**{title}**")
        B(pts)
    doc.add_heading("2. Your live-demo segment", 2)
    N(demo)
    doc.add_heading("3. Report sections you write", 2)
    B(report)
    doc.add_heading("4. Code you own (explain it line by line if asked)", 2)
    B(code)
    doc.add_heading("5. Theory you must master (from our course)", 2)
    B(theory)
    doc.add_heading("6. Viva questions to prepare (with model answers)", 2)
    QA(viva)
    doc.add_heading("7. Checklist", 2)
    B(["☐ " + c for c in checklist])
    brk()


member(
    "Saurav Singh",
    "S20230010219",
    "Problem & system lead (introduction, threat model, server, conclusion)",
    "Explain why cloud files need hybrid cryptography and what exactly we test, present the system architecture and the server side of the demo, and close the presentation.",
    [
        ("Title slide (≈30 s)", ["Introduce the group, the topic and the project type (research + application): we rebuilt a published scheme, attacked it, fixed it and measured it."]),
        (
            "Slide 1: Introduction & problem statement (≈1.5 min)",
            [
                "Cloud = our files on someone else's computer. Hybrid crypto: AES (fast) locks the file, ECC (public key) handles the key.",
                "Three attackers: outsider with a leaked copy, curious/malicious cloud insider, revoked user.",
                "Threat-model diagram: Alice → cloud → Bob/Charlie, attacker at the cloud.",
                "Problem statement + 4 objectives: rebuild, attack, fix, measure.",
            ],
        ),
        ("Slide 6, bottom: Conclusion (≈45 s)", ["Three conclusion bullets + future work (ML-KEM, key transparency). Hand over to the demo."]),
    ],
    [
        "Show the architecture in one sentence: React client (all crypto in the browser), Express API, MongoDB + GridFS.",
        "On the login page, set the Inspector to Step-by-step, log in as **alice**. Explain each step: the browser derives an auth token with PBKDF2 (the password is never sent); the server checks bcrypt; the browser opens the key vault with PBKDF2 (600,000 iterations) + AES-GCM.",
        "Optional (30 s): open **Register**, type a password and show the Shannon-entropy meter (Unit 2), then register `demo1` and show the two P-256 key pairs generated in the browser.",
        "Open **What the Cloud Sees**: explain that this is the raw database content (what a hacker with a leaked backup sees), and that the server log on this page updates live (Server-Sent Events).",
        "Hand over to Rohan: “Now let's upload a file with both schemes.”",
    ],
    [
        "Abstract; Section 1 (Introduction: topic, motivation, importance, problem statement, objectives, threat model, course mapping).",
        "Section 6 (implementation of the proposed approach: code structure, application walk-through, experimental setup table).",
        "Section 8 (Conclusion) and Appendix A (how to run the demo).",
    ],
    [
        "`app/server/src/` (`index.js`, `app.js`, `db.js`, `seed.js`, `models/*`, `routes/auth.js`, `routes/users.js`, `routes/files.js`, `lib/events.js`).",
        "`app/client/src/lib/session.jsx` (login/register flow), `pages/Login.jsx` (entropy meter), `pages/CloudView.jsx`.",
        "Key idea to explain: `deriveAuthToken` (PBKDF2 → sent to server, bcrypt stored) vs `sealPrivateKeys` (different PBKDF2 key with random salt, never leaves the browser).",
    ],
    [
        "**Shannon entropy (Unit 2):** H(X) = −Σ p(x) log₂ p(x). For bytes the maximum is 8 bits/byte (all 256 values equally likely). "
        f"Our ciphertext reaches {e3['proposed']['entropy_bits_per_byte']:.4f}; the base ECB image ciphertext only {e3['base']['entropy_bits_per_byte']:.2f}.",
        "**Key equivocation:** H(K | C) is the attacker's remaining uncertainty about the key. In the base scheme H(K | public key) = 0, because the key is a function of public data.",
        "**Perfect secrecy:** P(M | C) = P(M); needs |K| ≥ |M| (one-time pad). Real systems, including ours, are computationally secure instead.",
        "**Password entropy:** charset estimate L·log₂(N). Why PBKDF2 iterations slow down guessing (each guess costs 600,000 HMAC-SHA256 calls).",
        "**Hybrid cryptography idea:** symmetric for data + public key for key distribution (used in TLS, PGP).",
    ],
    [
        ("What is hybrid cryptography and why not use only RSA/ECC for the file?", "Public-key operations are slow and work on small inputs only. A symmetric cipher (AES) encrypts the bulk data quickly, and public-key cryptography solves how to give the AES key to the right people."),
        ("What is your threat model?", "The cloud provider can read and modify everything it stores. An outsider may obtain a leaked copy plus all public keys. A revoked user must not read new versions. We trust the users' own browsers and TLS."),
        ("What does an entropy of 7.9997 bits/byte mean?", "The byte values of the ciphertext are almost perfectly uniform, so no statistical pattern is left. The maximum for bytes is 8. The base scheme's image ciphertext has 6.55 because ECB keeps repeated blocks."),
        ("Why is H(K | P) = 0 in the base scheme?", "The AES key is computed as a function of the public key P. Once P is known (it is public), the key is completely determined, so no uncertainty is left."),
        ("Does the server ever see the password?", "No. The browser sends PBKDF2(password, username-salt) as a login token; the server stores bcrypt(token). The private keys are sealed with a different PBKDF2 key (random salt, 600k iterations), so even the server's database cannot open them."),
        ("Is your scheme perfectly secret?", "No. Perfect secrecy requires a key at least as long as the message (one-time pad). AES-GCM and ECDH are computationally secure: breaking them needs infeasible work (about 2¹²⁸ operations)."),
        ("What is GridFS?", "MongoDB's way to store large binary files in 255 KB chunks. We store only ciphertext there."),
    ],
    ["Can present Title + Slide 1 + Conclusion without notes", "Can run D1 smoothly in Step-by-step mode", "Report sections Abstract/1/6/8/App A proof-read", "Can explain auth token vs vault key", "Can derive and explain the entropy formula"],
)

member(
    "Rohan Dubey",
    "S20230010207",
    "Base-paper lead (technologies of the paper, its results, base implementation)",
    "Explain the base paper's technologies (AES, ECC, the hybrid AES-ECC algorithm) and its reported results, show our faithful re-implementation, and run the upload demo with both schemes.",
    [
        (
            "Slide 2: Technologies used in the paper (≈1.5 min)",
            [
                "AES: symmetric, 128-bit blocks, 10 rounds of SubBytes, ShiftRows, MixColumns (GF(2⁸)), AddRoundKey.",
                "ECC: curve y² = x³ + ax + b, private n, public P = n·G, ECDLP is hard; 256-bit ECC ≈ 3072-bit RSA.",
                "The paper's 4 steps (Box 1 + Box 2) and its claims; the authors' repository is empty, so we implemented it ourselves.",
            ],
        ),
        (
            "Slide 3: Results of the work (≈1.5 min)",
            [
                "The paper's Table 7 chart (hybrid 2.40–2.60 s vs AES 3.42–3.60 s), plus its claims (avalanche 61/64%, ECC:RSA 1:12, integrity).",
                f"Our reproduction works: 100/100 files, ≈{perf[16384]['base_enc_mbps']:.0f} MB/s, P-256 keygen {e9['p256_keygen_ms']:.2f} ms vs RSA-3072 {e9['rsa3072_keygen_ms']:.0f} ms.",
                "End with: “It is fast. But is it secure?” and hand over to Ujjawal.",
            ],
        ),
    ],
    [
        "Logged in as alice, Inspector in Step-by-step mode. Choose `payment_order.txt`, scheme **Base**, share with bob, click **Encrypt & upload**.",
        "Reveal the steps: the browser sends the PLAINTEXT; the CSP takes the x-coordinate of alice's public key, hashes it to get the AES key (point out: “no secret input”); encrypts with AES-ECB; 0 tag stored.",
        "Clear, select **Proposed**, upload the same file. Reveal: random DEK, AES-GCM with nonce and tag, ECDH key-wrap for alice and bob (show the shared secret), ECDSA signature, “DEK wiped”, and the server reporting it cannot decrypt.",
        "Open the proposed file as alice: show the 4 verification steps (signature, hash, unwrap with ECDH, GCM tag).",
        "Hand over to Ujjawal: “Both files are in the cloud. Let's attack them.”",
    ],
    [
        "Section 2 (overview of the article: technologies, methodology, reported results, advantages).",
        "Section 3 (implementation of the existing approach: tools, decisions table, code excerpt, setup, results).",
        "Section 9 (references): check every reference is complete and consistently formatted.",
    ],
    [
        "`app/crypto-core/src/base_aes_ecc.js`: `baseKeygen` (Box 1: P = n·G), `deriveAesKeyFromPublic` (Box 2), `baseEncrypt/baseDecrypt` (AES-ECB), traced versions.",
        "`app/client/src/pages/Dashboard.jsx` (Files page) and `uploadBase` in `lib/fileops.js`.",
        "Be ready to justify every decision in Table 4 of the report (curve, KDF, mode, server-side encryption) with a quote from the paper.",
    ],
    [
        "**Number theory (Unit 1):** modular arithmetic, modular inverse via the extended Euclidean algorithm, used in ECC point addition (slope λ = (y₂−y₁)/(x₂−x₁) mod p).",
        "**AES (Module 3):** state 4×4 bytes; S-box = inverse in GF(2⁸) + affine map; MixColumns = matrix over GF(2⁸) with m(x) = x⁸+x⁴+x³+x+1; key expansion (44 words for AES-128); 10/12/14 rounds.",
        "**ECC (Module 4):** point addition and doubling, scalar multiplication by double-and-add, ECDLP; NIST P-256; why ECC keys are smaller than RSA keys (best attack on ECC is Pollard's rho ≈ √n, while RSA has sub-exponential factoring algorithms).",
        "**RSA basics for comparison:** n = pq, e·d ≡ 1 mod φ(n). RSA-3072 key generation is slow because it needs large primes.",
    ],
    [
        ("Explain one AES round.", "SubBytes replaces each byte through the S-box (non-linear, confusion), ShiftRows rotates the rows, MixColumns mixes each column with a fixed matrix over GF(2⁸) (diffusion), and AddRoundKey XORs the round key. AES-128 has 10 rounds, and the last round skips MixColumns."),
        ("What is P = n·G and why is it secure?", "G is a fixed base point and n is the private number. n·G means adding G to itself n times (done quickly with double-and-add). Getting n back from P is the elliptic-curve discrete-log problem, for which no efficient algorithm is known."),
        ("Why is 256-bit ECC as strong as 3072-bit RSA?", "The best known attack on ECC (Pollard's rho) takes about √n ≈ 2¹²⁸ steps for a 256-bit curve. RSA can be attacked with sub-exponential factoring (the number field sieve), so it needs a 3072-bit modulus for 128-bit security (NIST SP 800-57)."),
        ("How exactly did you build the AES key in the base scheme? Isn't that your mistake?", "The paper's Box 2 says AES encryption is performed “using the public key which is generated by ECC”, and it says the public key is known by everyone. We used SHA-256 of P's x-coordinate. Any function of the public key has the same flaw, because the attacker can compute it too."),
        ("Why is a “64-bit AES key” wrong?", "FIPS-197 defines AES only for 128, 192 and 256-bit keys. A 64-bit AES does not exist, so the paper's 64-bit rows cannot be real AES."),
        ("Can a hybrid AES+ECC scheme be faster than AES alone?", "Not if it uses the same AES implementation, because it does all the AES work plus ECC work. A faster result means different implementations or data were compared."),
        ("Why did you write your own implementation?", "The repository linked in the paper contains only a README, with no code. We followed Box 1 and Box 2 and documented every choice the paper leaves open."),
    ],
    ["Can present Slides 2–3 without notes", "Can run D2 in Step-by-step mode", "Sections 2, 3 and 9 proof-read", "Can draw one AES round and the ECC point-addition picture on the board", "Can justify the base-scheme implementation choices"],
)

member(
    "Ujjawal",
    "S20230010245",
    "Security analyst (weaknesses, attacks, statistical analysis)",
    "Find and prove the weaknesses of the base paper. Present the three challenges, run the live attacks, and explain the measurements (entropy, repeated blocks, avalanche).",
    [
        (
            "Slide 4: Weaknesses of the paper, 3 challenges (≈2 min)",
            [
                f"C1: the key comes from the PUBLIC key, so {e1['base_recovered']}/{e1['files']} files were decrypted with public data only (Kerckhoffs; H(K|P)=0).",
                f"C2: no integrity check and ECB-style mode: 0/{T2:,} tampering attempts detected; image patterns stay visible; payment amounts swapped.",
                "C3: no real sharing or revocation: the cloud encrypts, so it sees the plaintext; revocation changes no key; problems in the paper's evaluation (64-bit AES, avalanche >50%, power = time, empty repository).",
            ],
        )
    ],
    [
        "Open **Attack Lab**; select the base and proposed `payment_order.txt`. Inspector: Step-by-step.",
        "Attack 1: click **Attack the BASE file** and reveal the attacker steps (gets the ciphertext → reads alice's public key → applies the paper's rule → full plaintext). Then **Attack the PROPOSED file**: all candidate keys fail the GCM tag.",
        "Attack 2: choose “Swap ciphertext blocks 2 ↔ 4”. **Tamper BASE** → **Open as me**: the amounts are swapped and there is no warning. **Tamper PROPOSED** → **Open as me**: BLOCKED, and the Inspector shows that the hash no longer matches the signed manifest. Click **Restore originals**.",
        "Attack 3: **Run with sample logo**: the logo stays visible in the AES-ECB ciphertext and the GCM ciphertext looks like noise. Read out the entropy and repeated-block numbers under the images.",
        "Hand over to Aditya: “Now the sharing and revocation part.”",
    ],
    [
        "Section 4 (challenges and limitations: C1, C2, C3, evaluation issues, summary table).",
        "Sections 7.1–7.5 (summary table, attack 1, attack 2, entropy/patterns/determinism, avalanche re-evaluation).",
    ],
    [
        "`app/server/src/routes/lab.js` (public-key attack, tamper/restore, ECB endpoint).",
        "`app/client/src/pages/AttackLab.jsx` and `app/crypto-core/src/analysis.js` (Shannon entropy, repeated-block ratio, chi-square, bit difference).",
        "`app/bench/run.js` experiments E1–E5 (how “detected” vs “silent corruption” is counted).",
    ],
    [
        "**Block cipher modes (Module 3):** ECB, CBC, CFB, OFB, CTR. ECB encrypts equal blocks to equal ciphertext, so patterns leak. CBC/CTR need an IV/nonce. No basic mode gives integrity on its own.",
        "**Malleability:** in ECB, ciphertext blocks can be swapped or deleted; in CBC, flipping a bit in Cᵢ flips the same bit in Pᵢ₊₁; in CTR, flipping a ciphertext bit flips the same plaintext bit.",
        "**Kerckhoffs' principle** and classical-cipher lessons (frequency analysis works because structure survives encryption, just like ECB).",
        "**Avalanche / strict avalanche criterion:** a 1-bit change should flip each output bit with probability ½, so 50% is ideal. Our AES measurement is ≈49.9%.",
        "**Statistics:** Shannon entropy per byte, repeated-block ratio, chi-square against the uniform distribution (≈255 expected for random bytes).",
    ],
    [
        ("Why does ECB leak the picture?", "Each 16-byte block is encrypted separately with the same key, so equal pixel blocks (flat colours) produce equal ciphertext blocks. The outline of the image therefore survives encryption."),
        ("How could the cloud swap the payment amounts without knowing the key?", "In ECB each block decrypts independently. Swapping ciphertext blocks 2 and 4 swaps plaintext blocks 2 and 4, which hold the two amount lines. With no MAC, nothing detects the change."),
        ("Would switching the base scheme to CBC fix it?", "No. The key would still be computed from the public key (C1). CBC is also malleable and, without a MAC, open to padding-oracle attacks (Vaudenay 2002). Only authenticated encryption fixes integrity."),
        ("The paper reports 64% avalanche. Isn't higher better?", "No. The ideal is 50%: each output bit should flip with probability ½. 64% means the bits are biased (a 100% flip would simply be the complement). Our measurement of AES gives ≈49.9%."),
        ("What is Kerckhoffs' principle and how does the base scheme break it?", "A cryptosystem should stay secure even if everything except the key is public. The base scheme's key is itself computed from public information, so nothing secret remains."),
        ("How did you decide that a tampering attempt was “detected”?", "Detected means decryption raised an error and released nothing. Silent corruption means it returned plaintext different from the original. The base scheme detected 0; ours detected 100%."),
        ("Why is the base ciphertext entropy 6.55 and not 8 even though AES is used?", "AES-ECB maps the many repeated plaintext blocks to the same few ciphertext blocks, so some byte patterns are much more frequent than others. A good mode with a fresh nonce makes every block different."),
    ],
    ["Can present Slide 4 without notes", "Can run D3 (attacks 1–3) and restore the originals", "Sections 4 and 7.1–7.5 proof-read", "Can explain ECB/CBC/CTR on the board", "Can explain the avalanche criterion and the entropy numbers"],
)

member(
    "Aditya Raj",
    "S20230030364",
    "Solution lead (proposed AHE scheme, improved results)",
    "Design and explain the improved scheme (random key, AES-GCM, ECDH key wrapping, ECDSA signatures, re-keying), present the improved results, and demonstrate sharing and revocation.",
    [
        (
            "Slide 5: Our fix, the authenticated hybrid envelope (≈2 min)",
            [
                "5 steps: random DEK → AES-256-GCM (+tag) → lock the key for each user with ECDH + HKDF → owner signs with ECDSA → the cloud stores only ciphertext. Each step names the challenge it fixes.",
                "Opening: verify signature → check hash → unlock with my private key → decrypt + tag check. Any failure → BLOCKED.",
                f"Sharing adds one locked key ({e7['add_recipient_later_ms']:.1f} ms). Revocation re-keys to version 2 ({rev[1024]['rekey_ms']:.1f} ms/MiB). Everything comes from course topics.",
            ],
        ),
        (
            "Slide 6, top: Results after the fix (≈1.5 min)",
            [
                f"Table: {e1['base_recovered']}/{e1['files']} → {e1['proposed_recovered']}/{e1['files']}; 0% → 100% tampering detected; 98% → 0% repeated blocks; entropy 6.55 → 8.00; revocation impossible → possible.",
                f"Cost: ≈{perf[1]['proposed_enc_ms']:.0f} ms per file; 16 MiB in {perf[16384]['proposed_enc_ms']:.0f} ms (≈{perf[16384]['proposed_enc_mbps']:.0f} MB/s). Hand over to Saurav for the conclusion.",
            ],
        ),
    ],
    [
        "As alice: upload `salary_records.csv` with **Proposed**, shared with bob and charlie.",
        "In bob's window (incognito): **Refresh**, **Open** the file. Reveal the steps: ECDSA verify, hash check, ECDH unwrap (shared secret S = d·R), GCM decrypt.",
        "As alice: **Share / Revoke** → **Revoke** bob. Reveal: decrypt, new random DEK, re-encrypt as version 2, wrap only for alice + charlie, sign.",
        "In bob's window: **Refresh**. The file shows “access revoked”. Click **Open**: the server still sends the new ciphertext, but bob has no wrapped key, so access is DENIED by cryptography.",
        "Open **Results**: tampering chart, entropy chart, time vs size, avalanche table. End: “All numbers are generated by `npm run bench` with the same code.”",
    ],
    [
        "Section 5 (proposed approach: selected challenges, design principles, building blocks, pseudocode, security analysis, limitations).",
        "Sections 7.6–7.8 (performance, sharing and revocation, challenge-by-challenge outcome).",
    ],
    [
        "`app/crypto-core/src/proposed_ahe.js`: `encryptFile`, `decryptFile`, `wrapDek` / `unwrapDek` (ECDH + HKDF + AES-GCM), `addRecipient`, `rekeyFile`, `publicKeyAttackOnProposed`.",
        "`app/client/src/lib/fileops.js` (`uploadProposed`, `openFile`, `shareFile`, `revokeUser`), `app/client/src/pages/Results.jsx`.",
        "`app/bench/run.js` experiments E6–E9 (performance, sharing, revocation, primitives) and `app/crypto-core/test/crypto.test.js`.",
    ],
    [
        "**Diffie-Hellman (Unit 6) → ECDH:** Alice sends R = r·G, Bob has Q = d·G; both compute S = r·Q = d·R = rd·G. An eavesdropper sees R and Q but cannot get S (ECDH problem).",
        "**Key management (Unit 6):** hybrid KEM/DEM (ECIES), one wrapped key per recipient, revocation by re-keying, why the server must not hold keys.",
        "**Hash functions (Module 5):** SHA-256 properties (pre-image and collision resistance, avalanche); HKDF = HMAC-based extract-then-expand.",
        "**Digital signatures (Module 5):** DSA/ElGamal-style signatures; ECDSA = DSA on elliptic curves (r = (k·G).x mod n, s = k⁻¹(H(m) + d·r) mod n); the nonce k must never repeat.",
        "**AES-GCM:** CTR mode for encryption + GHASH (polynomial evaluation in GF(2¹²⁸)) for a 128-bit tag; the 96-bit nonce must never repeat under the same key; associated data is authenticated but not encrypted.",
    ],
    [
        ("How does GCM detect tampering?", "It computes a 128-bit tag over the ciphertext and the associated data using GHASH, keyed from the AES key. Decryption recomputes the tag; if even one bit changed the tags differ and decryption is refused. A forgery succeeds with probability about 2⁻¹²⁸ per try."),
        ("Explain your key wrapping. Where is Diffie-Hellman?", "For each recipient we pick a fresh r, publish R = r·G, compute S = r·Q with the recipient's public key Q, derive a KEK with HKDF, and encrypt the DEK with AES-GCM. The recipient computes S = d·R with their private key d. This is Diffie-Hellman key agreement on the elliptic curve, as in ECIES."),
        ("Why HKDF? Why not use S directly as the key?", "S is a curve coordinate, not a uniformly random string. HKDF extracts its entropy and binds the key to the context (fileId, version, recipient, R), so keys for different files or versions are independent."),
        ("GCM already authenticates. Why sign as well?", "Every recipient knows the DEK, so any recipient could produce a valid GCM ciphertext. Only the owner holds the ECDSA private key, so the signature proves who uploaded the file and protects the manifest (recipients, version, hash)."),
        ("How does revocation work, and what are its limits?", "We decrypt, generate a new DEK, re-encrypt as version+1 and wrap the key only for the remaining users. The old wrapped key cannot open the new version (the version is bound in the associated data). A revoked user can still keep data they already downloaded."),
        ("What does security cost?", f"About {perf[1]['proposed_enc_ms']:.0f} ms per file for two ECDH operations, one signature and key imports, plus GCM and SHA-256 over the data: 16 MiB takes {perf[16384]['proposed_enc_ms']:.0f} ms instead of {perf[16384]['base_enc_ms']:.0f} ms. That is still hundreds of MB/s, faster than any upload."),
        ("Is your scheme novel?", "No. It is a careful combination of standard constructions (ECIES-style KEM, AEAD, signatures), similar to what modern secure messaging and file-encryption tools use. Our contribution is finding the flaws in the published scheme, applying these standard fixes, implementing them, and measuring both schemes under identical attacks."),
    ],
    ["Can present Slide 5 and the results of Slide 6 without notes", "Can run D4 with two browser windows", "Sections 5 and 7.6–7.8 proof-read", "Can write the ECDH and ECDSA equations on the board", "Can explain why GCM + signature are both needed"],
)

# ================================================================== common
doc.add_heading("Questions anyone may be asked", 1)
QA(
    [
        ("Which paper did you choose and why?", "Rehman et al., “Hybrid AES-ECC Model for the Security of Data over Cloud Storage”, Electronics 10(21):2673, 2021 (MDPI, peer reviewed, open access). It matches our topic, uses AES and ECC from our syllabus, and its full text is available."),
        ("Is this a survey?", "No. It is a research + application project: we implemented one published scheme, analysed it with experiments, and implemented and evaluated an improvement."),
        ("Why MERN?", "It gives a realistic cloud setting: a browser client (where end-to-end encryption must happen), a REST server, and a document database with GridFS for blobs. WebCrypto in the browser and Node's OpenSSL give standard, audited primitives."),
        ("Did you use any cryptography library you don't understand?", "We used only standard primitives (AES, SHA-256, ECDH, ECDSA, HKDF, PBKDF2) from the browser's Web Crypto API and Node's OpenSSL. We did not invent any cipher; the design and the analysis are ours."),
        ("Where do your numbers come from?", "From `app/bench/run.js`, which runs the same crypto code as the app. Results are saved in `results.json`, and the slides, report and app read that file, so all numbers match."),
    ]
)
doc.save(OUT)
print("saved", OUT)
