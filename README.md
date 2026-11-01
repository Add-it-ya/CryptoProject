# Group 18: Secure Cloud File Sharing Using Hybrid Cryptography

**Cryptography course project (Research + Application).**
Saurav Singh (S20230010219) · Rohan Dubey (S20230010207) · Ujjawal (S20230010245) · Aditya Raj (S20230030364)

We re-implemented the **Hybrid AES-ECC model** of Rehman et al. (*Electronics* 10(21):2673, 2021), attacked it,
found three weaknesses, and fixed them with an **Authenticated Hybrid Envelope (AHE)**: a random per-file key,
AES-256-GCM, ECDH (P-256) + HKDF key wrapping per recipient, ECDSA signatures, client-side encryption and re-keying.

| Result (same experiments) | Base AES-ECC | Our AHE |
|---|---|---|
| Files decrypted using only public data | 100 / 100 | 0 / 100 |
| Tampering detected (1,250 attacks) | 0 % | 100 % |
| Repeated 16-byte blocks in encrypted image | 98.2 % | 0 % |
| Ciphertext entropy (bits/byte, max 8) | 6.55 | 8.00 |
| Revoke a user | impossible | 7.6 ms per MiB |

## Folder layout

```
presentation/   Group18_Secure_Cloud_File_Sharing.pptx  (title + 6 slides, animations, speaker notes)
                Group18_Secure_Cloud_File_Sharing_preview.pdf
                build/  (custom theme generator + deck builder, python-pptx)
report/         Group18_Project_Report.docx / .pdf  (22 pages)
                figures/, screenshots/, build/
team/           Group18_Task_Division.docx / .pdf  (one independent brief per member + viva Q&A)
app/            CryptoVault demo (MERN)
  crypto-core/  shared crypto: base_aes_ecc.js (paper), proposed_ahe.js (ours), analysis.js
  server/       Express + MongoDB/GridFS API, Attack Lab, live log (SSE)
  client/       React app: Files, Attack Lab, What the Cloud Sees, Results, Crypto Inspector
  bench/        experiment harness (E1-E9) -> bench/results/results.json
  e2e/          Playwright script that drives the app and captures the report screenshots
analysis/       figure generators (matplotlib)
```

## Run the demo

Requires Node.js 20.19+ (22 LTS recommended) and a MongoDB database (MongoDB Atlas or a local MongoDB server).

1. Put your MongoDB URL in **`app/server/.env`** (the file is already there; only `MONGO_URI` must be filled):
   ```
   MONGO_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/cryptovault?retryWrites=true&w=majority
   ```
   URL-encode special characters in the password (`@` → `%40`, `#` → `%23`). For Atlas, allow your IP under *Network Access*.
2. Install and start:
   ```bash
   cd app
   npm install
   npm test            # 5 crypto unit tests
   npm start           # builds the client and serves everything on http://localhost:5000
   ```
   The console prints `[db] connected: <host> / database "cryptovault"`, and `http://localhost:5000/api/health` shows `"db":"connected"`.
   If the URL is missing or wrong, the server stops with a message explaining what to check.

On the first start, the demo users are created in that database: `alice / Alice@Cloud2026`, `bob / Bob@Cloud2026`,
`charlie / Charlie@Cloud2026`, `mallory / Mallory@Cloud2026`. Data stays in your MongoDB between runs.
Use a normal window for alice and a private/incognito window for bob. In the **Crypto Inspector**, choose
**Step-by-step** and press **Next ▶** to reveal each real cryptographic step (keys, nonces, ECDH secrets, tags, signatures).

For development with hot reload, run `npm run dev` (client on :5173, API on :5000).
Do not share `app/server/.env` (it contains your database password).

## Regenerate results, figures, slides and report

```bash
cd app && npm run bench                     # -> bench/results/results.json
cd .. && python3 analysis/make_figures.py app/bench/results/results.json app/bench/results report/figures
cd presentation/build && python3 theme_assets.py assets ../../app/bench/results \
  && python3 build_deck.py assets ../../app/bench/results/results.json ../Group18_Secure_Cloud_File_Sharing.pptx
cd ../../report && python3 build/build_report.py ../app/bench/results/results.json figures screenshots Group18_Project_Report.docx
```
(Python needs `python-pptx python-docx matplotlib pillow numpy`.)
