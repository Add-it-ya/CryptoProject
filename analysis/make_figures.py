"""Report figures (print-friendly, light theme) from bench/results/results.json.
usage: python3 make_figures.py <results.json> <bench_results_dir> <out_dir>"""
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from PIL import Image

RES, BDIR, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)
R = json.load(open(RES))

RED = "#d9485f"
GREEN = "#0f9d76"
BLUE = "#1d6fb8"
AMBER = "#d99a00"
VIOLET = "#7b5cd6"
GREY = "#6b7a90"
INK = "#14213d"
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.edgecolor": "#9aa7b8",
        "axes.labelcolor": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": "#e3e8ef",
        "grid.linewidth": 0.8,
        "axes.axisbelow": True,
        "figure.dpi": 200,
    }
)


def save(fig, name):
    fig.savefig(os.path.join(OUT, name), bbox_inches="tight", facecolor="white")
    plt.close(fig)


# --------------------------------------------------------------- tampering
e2 = R["e2_tampering"]
names = {"bit_flip": "Bit flip", "block_swap": "Block swap", "block_delete": "Block delete", "splice_other_file": "Splice other file", "manifest_edit": "Swap file / edit manifest"}
ks = list(e2.keys())
fig, ax = plt.subplots(figsize=(7.2, 3.0))
x = range(len(ks))
bd = [100 * e2[k]["base"]["detected"] / e2[k]["trials"] for k in ks]
pd = [100 * e2[k]["proposed"]["detected"] / e2[k]["trials"] for k in ks]
ax.bar([i - 0.2 for i in x], bd, 0.4, color=RED, label="Base AES-ECC")
ax.bar([i + 0.2 for i in x], pd, 0.4, color=GREEN, label="Proposed AHE")
for i in x:
    ax.text(i - 0.2, bd[i] + 2, f"{bd[i]:.0f}%", ha="center", fontsize=8, color=RED)
    ax.text(i + 0.2, pd[i] + 2, f"{pd[i]:.0f}%", ha="center", fontsize=8, color=GREEN)
ax.set_xticks(list(x))
ax.set_xticklabels([names[k] for k in ks], fontsize=8.5)
ax.set_ylabel("Tampering detected (%)")
ax.set_ylim(0, 112)
ax.legend(frameon=False, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.14))
save(fig, "fig_tamper.png")

# --------------------------------------------------------------- performance
rows = R["e6_performance"]
sz = [r["size_kib"] / 1024 for r in rows]
fig, axs = plt.subplots(1, 2, figsize=(7.4, 2.9))
ax = axs[0]
ax.plot(sz, [r["base_enc_ms"] for r in rows], "o-", color=RED, label="Base encrypt")
ax.plot(sz, [r["proposed_enc_ms"] for r in rows], "s-", color=GREEN, label="Proposed encrypt")
ax.plot(sz, [r["base_dec_ms"] for r in rows], "o--", color=RED, alpha=0.5, label="Base decrypt")
ax.plot(sz, [r["proposed_dec_ms"] for r in rows], "s--", color=GREEN, alpha=0.5, label="Proposed decrypt")
ax.set_xscale("log", base=2)
ax.set_yscale("log")
ax.set_xticks(sz)
ax.set_xticklabels([f"{r['size_kib']}K" if r["size_kib"] < 1024 else f"{r['size_kib'] // 1024}M" for r in rows], fontsize=7.5)
ax.minorticks_off()
ax.set_xlabel("File size (bytes, log scale)")
ax.set_ylabel("Time (ms, log)")
ax.legend(frameon=False, fontsize=7.5)
ax.set_title("Time vs. file size (median)", fontsize=10)
ax = axs[1]
big = [r for r in rows if r["size_kib"] >= 256]
xs = range(len(big))
ax.bar([i - 0.2 for i in xs], [r["base_enc_mbps"] for r in big], 0.4, color=RED, label="Base")
ax.bar([i + 0.2 for i in xs], [r["proposed_enc_mbps"] for r in big], 0.4, color=GREEN, label="Proposed")
ax.set_xticks(list(xs))
ax.set_xticklabels([f"{r['size_kib'] // 1024 if r['size_kib'] >= 1024 else r['size_kib']}{' MiB' if r['size_kib'] >= 1024 else ' KiB'}" for r in big], fontsize=8)
ax.set_ylabel("Encryption throughput (MB/s)")
ax.legend(frameon=False, fontsize=8)
ax.set_title("Throughput", fontsize=10)
fig.tight_layout()
save(fig, "fig_perf.png")

# --------------------------------------------------------------- sharing + revocation
e7 = R["e7_sharing"]["rows"]
e8 = R["e8_revocation"]
fig, axs = plt.subplots(1, 2, figsize=(7.4, 2.7))
ax = axs[0]
ax.plot([r["recipients"] for r in e7], [r["encrypt_and_share_ms"] for r in e7], "o-", color=VIOLET)
ax2 = ax.twinx()
ax2.plot([r["recipients"] for r in e7], [r["manifest_bytes"] / 1024 for r in e7], "s--", color=AMBER)
ax2.set_ylabel("Manifest size (KiB)", color=AMBER)
ax2.grid(False)
ax2.spines["right"].set_visible(True)
ax.set_xlabel("Recipients (1 MiB file)")
ax.set_ylabel("Encrypt + share (ms)", color=VIOLET)
ax.set_title("Sharing cost grows linearly", fontsize=10)
ax = axs[1]
ax.bar([f"{r['size_kib'] // 1024} MiB" if r["size_kib"] >= 1024 else f"{r['size_kib']} KiB" for r in e8], [r["rekey_ms"] for r in e8], color=BLUE)
for i, r in enumerate(e8):
    ax.text(i, r["rekey_ms"] + 1, f"{r['rekey_ms']:.1f}", ha="center", fontsize=8)
ax.set_ylabel("Re-key time (ms)")
ax.set_title("Revocation (re-key) cost", fontsize=10)
fig.tight_layout()
save(fig, "fig_share_revoke.png")

# --------------------------------------------------------------- entropy / avalanche
e3 = R["e3_ecb_image"]
e5 = R["e5_avalanche"]
fig, axs = plt.subplots(1, 2, figsize=(7.4, 2.7))
ax = axs[0]
labs = ["Original", "Base (ECB)", "Proposed (GCM)"]
ent = [e3["original"]["entropy_bits_per_byte"], e3["base"]["entropy_bits_per_byte"], e3["proposed"]["entropy_bits_per_byte"]]
rep = [e3["original"]["repeated_block_pct"], e3["base"]["repeated_block_pct"], e3["proposed"]["repeated_block_pct"]]
b = ax.bar(labs, ent, color=[GREY, RED, GREEN])
for i, v in enumerate(ent):
    ax.text(i, v + 0.15, f"{v:.2f}\n({rep[i]:.0f}% rep.)", ha="center", fontsize=8)
ax.set_ylim(0, 9.8)
ax.axhline(8, color=INK, lw=0.8, ls=":")
ax.set_ylabel("Shannon entropy (bits/byte)")
ax.set_title("Image ciphertext statistics", fontsize=10)
ax = axs[1]
labs = ["AES, key\n(paper)", "AES, key\n(ours)", "Hybrid\n(paper)", "File: base\n(ours)", "File: ours\n(ours)"]
vals = [e5["paper_reported"]["aes_key"], e5["aes_block_1bit_key_change_pct"], e5["paper_reported"]["proposed_key"], e5["whole_file_4KiB_base_pct"], e5["whole_file_4KiB_proposed_pct"]]
cols = [GREY, BLUE, AMBER, RED, GREEN]
ax.bar(labs, vals, color=cols)
for i, v in enumerate(vals):
    ax.text(i, v + 1.5, f"{v:.1f}%", ha="center", fontsize=8)
ax.axhline(50, color=INK, lw=0.9, ls="--")
ax.text(2.55, 53, "ideal = 50%", fontsize=7.5, ha="center")
ax.set_ylim(0, 75)
ax.tick_params(axis="x", labelsize=7.5)
ax.set_ylabel("Bits changed (%)")
ax.set_title("Avalanche: 1-bit change", fontsize=10)
fig.tight_layout()
save(fig, "fig_entropy_avalanche.png")

# --------------------------------------------------------------- paper's reported results
fig, ax = plt.subplots(figsize=(6.4, 2.7))
cats = ["64", "128", "192", "256"]
series = [("Hybrid AES-ECC", (2.40, 2.47, 2.54, 2.60), AMBER), ("AES", (3.42, 3.59, 3.48, 3.60), BLUE), ("DES", (3.89, 4.02, 4.05, 4.34), VIOLET), ("Blowfish", (4.31, 4.47, 4.43, 4.70), GREY)]
for j, (n, v, c) in enumerate(series):
    ax.bar([i + (j - 1.5) * 0.2 for i in range(4)], v, 0.2, label=n, color=c)
ax.set_xticks(range(4))
ax.set_xticklabels([f"{c}-bit key" for c in cats])
ax.set_ylabel("Encryption time (s)")
ax.legend(frameon=False, ncol=4, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, 1.16))
save(fig, "fig_paper_results.png")

# --------------------------------------------------------------- ECB panel
ims = [Image.open(os.path.join(BDIR, n + ".bmp")).convert("RGB") for n in ["ecb_original", "ecb_base_encrypted", "ecb_proposed_encrypted"]]
fig, axs = plt.subplots(1, 3, figsize=(7.4, 2.1))
for ax, im, t in zip(axs, ims, ["(a) original image", "(b) base: AES-ECB ciphertext", "(c) proposed: AES-256-GCM ciphertext"]):
    ax.imshow(im)
    ax.set_title(t, fontsize=9)
    ax.axis("off")
fig.tight_layout()
save(fig, "fig_ecb.png")


# --------------------------------------------------------------- diagrams
def node(ax, x, y, w, h, txt, fc, ec, fs=8.5, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.06", fc=fc, ec=ec, lw=1.2))
    ax.text(x + w / 2, y + h / 2, txt, ha="center", va="center", fontsize=fs, color=INK, fontweight="bold" if bold else "normal", wrap=True)


def arrow(ax, x0, y0, x1, y1, c=INK, txt=None, fs=7.5, dy=0.05, ls="-"):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=11, color=c, lw=1.2, linestyle=ls))
    if txt:
        ax.text((x0 + x1) / 2, (y0 + y1) / 2 + dy, txt, ha="center", fontsize=fs, color=c)


def canvas(w=7.4, h=2.6):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.5)
    ax.axis("off")
    return fig, ax


# base flow
fig, ax = canvas(7.4, 2.5)
node(ax, 0.1, 1.3, 1.25, 0.9, "User\n(browser)", "#eaf2fb", BLUE, bold=True)
node(ax, 2.35, 1.3, 1.5, 0.9, "CSP\nverification", "#f3eefc", VIOLET)
node(ax, 4.6, 2.25, 2.4, 0.9, "Box 1: ECC keys\nP = n(a)·G", "#fff6dd", AMBER)
node(ax, 4.6, 0.45, 2.4, 0.9, "Box 2: K = H(P.x)\nAES-ECB(K, file)", "#fdecef", RED)
node(ax, 8.1, 1.3, 1.8, 0.9, "Cloud\nstorage", "#eef1f5", GREY, bold=True)
arrow(ax, 1.35, 1.75, 2.35, 1.75, BLUE, "plaintext", dy=0.1)
arrow(ax, 3.85, 1.9, 4.6, 2.55, INK)
arrow(ax, 5.8, 2.25, 5.8, 1.35, AMBER)
ax.text(5.9, 1.75, "public key P", fontsize=7.5, color=AMBER)
arrow(ax, 3.85, 1.6, 4.6, 0.95, INK)
arrow(ax, 7.0, 0.9, 8.1, 1.55, RED)
ax.text(7.25, 0.85, "ciphertext", fontsize=7.5, color=RED)
ax.text(5, 0.02, "Every input of the AES key is public; the CSP sees the plaintext; nothing authenticates the ciphertext.", ha="center", fontsize=7.8, color=RED, style="italic")
save(fig, "fig_base_flow.png")

# proposed flow
fig, ax = canvas(7.4, 3.2)
ax.set_ylim(0, 4.3)
ax.add_patch(FancyBboxPatch((0.05, 0.55), 6.35, 3.55, boxstyle="round,pad=0.02,rounding_size=0.1", fc="#f5fbf8", ec=GREEN, lw=1, ls="--"))
ax.text(0.2, 3.85, "Browsers (WebCrypto): keys never leave them", fontsize=8, color=GREEN, fontweight="bold")
node(ax, 0.2, 2.7, 1.9, 0.9, "① Random DEK\n(256-bit CSPRNG)", "#e9f7f1", GREEN, fs=7.8)
node(ax, 2.3, 2.7, 1.9, 0.9, "② AES-256-GCM\n(+ 128-bit tag)", "#e9f7f1", GREEN, fs=7.8)
node(ax, 4.4, 2.7, 1.9, 0.9, "④ ECDSA sign\nthe manifest", "#e9f7f1", GREEN, fs=7.8)
node(ax, 0.2, 0.75, 2.95, 1.45, "③ Wrap DEK for each\nrecipient j:  S = r·Qj (ECDH)\nKEK = HKDF(S)", "#eaf2fb", BLUE, fs=7.8)
node(ax, 3.35, 0.75, 2.95, 1.45, "Recipient j: verify signature,\ncheck hash, S = dj·R,\nunwrap DEK, GCM decrypt", "#f3eefc", VIOLET, fs=7.8)
node(ax, 7.3, 1.55, 2.6, 1.4, "Cloud stores only\nciphertext + manifest\n+ signature", "#eef1f5", GREY, fs=7.8)
arrow(ax, 2.1, 3.15, 2.3, 3.15, GREEN)
arrow(ax, 4.2, 3.15, 4.4, 3.15, GREEN)
arrow(ax, 1.15, 2.7, 1.15, 2.2, BLUE)
arrow(ax, 6.3, 3.0, 7.3, 2.6, INK)
ax.text(6.55, 3.05, "upload", fontsize=7.5)
arrow(ax, 7.3, 1.8, 6.3, 1.45, VIOLET)
ax.text(6.45, 1.25, "download", fontsize=7.5, color=VIOLET)
ax.text(5, 0.15, "The server never holds the DEK or a private key; revocation = new DEK + version + 1.", ha="center", fontsize=7.8, color=GREEN, style="italic")
save(fig, "fig_proposed_flow.png")

# architecture
fig, ax = canvas(7.4, 2.9)
ax.set_ylim(0, 3.9)
node(ax, 0.1, 0.35, 3.5, 3.25, "", "#eaf2fb", BLUE)
ax.text(1.85, 3.28, "React client (Vite)", ha="center", fontsize=8.5, fontweight="bold", color=BLUE)
for i, t in enumerate(["Files: upload/open/share/revoke", "Attack Lab", "Cloud view · Results", "crypto-core (WebCrypto)", "Crypto Inspector (live trace)"]):
    node(ax, 0.25, 2.6 - i * 0.5, 3.2, 0.4, t, "white", BLUE, fs=7.3)
node(ax, 4.05, 0.35, 3.3, 3.25, "", "#f3eefc", VIOLET)
ax.text(5.7, 3.28, "Express API (Node.js)", ha="center", fontsize=8.5, fontweight="bold", color=VIOLET)
for i, t in enumerate(["/auth: bcrypt + JWT", "/files: base (server AES-ECC)", "/files: proposed (opaque)", "/lab: attacker simulation", "/events: live SSE log"]):
    node(ax, 4.2, 2.6 - i * 0.5, 3.0, 0.4, t, "white", VIOLET, fs=7.3)
node(ax, 7.85, 1.0, 2.05, 1.9, "MongoDB\nusers, files\nGridFS blobs", "#eef1f5", GREY, fs=7.8)
arrow(ax, 3.6, 2.25, 4.05, 2.25, INK)
ax.text(3.83, 2.35, "REST", fontsize=6.8, ha="center")
arrow(ax, 4.05, 1.4, 3.6, 1.4, VIOLET)
ax.text(3.83, 1.5, "SSE", fontsize=6.8, ha="center", color=VIOLET)
arrow(ax, 7.35, 1.95, 7.85, 1.95, INK)
save(fig, "fig_architecture.png")
print("figures written to", OUT)
