// =============================================================================================
// Group 18 - experiment harness.  Runs every security + performance experiment used in the
// report and slides, on the SAME crypto code that the MERN demo app uses.
//   node bench/run.js            (full run, ~1-2 min)
//   node bench/run.js --quick    (smaller sizes, for a quick check)
// Output: bench/results/results.json  (+ BMP images for the ECB experiment)
// =============================================================================================
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { baseKeygen, baseEncrypt, baseDecrypt, publicKeyAttack, deriveAesKeyFromPublic } from '../crypto-core/src/base_aes_ecc.js';
import {
  generateUserKeys,
  exportPublicRaw,
  encryptFile,
  decryptFile,
  addRecipient,
  rekeyFile,
  publicKeyAttackOnProposed,
  IntegrityError,
} from '../crypto-core/src/proposed_ahe.js';
import { randomBytes, te, bytesEqual } from '../crypto-core/src/encoding.js';
import { shannonEntropy, repeatedBlockRatio, chiSquare, bitDifference } from '../crypto-core/src/analysis.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(HERE, 'results');
fs.mkdirSync(OUT, { recursive: true });
const QUICK = process.argv.includes('--quick');
const log = (...a) => console.log('[bench]', ...a);
const median = (a) => {
  const s = [...a].sort((x, y) => x - y);
  return s.length % 2 ? s[(s.length - 1) / 2] : (s[s.length / 2 - 1] + s[s.length / 2]) / 2;
};
const rnd = (n) => crypto.randomInt(n);

async function mkUser(id) {
  const keys = await generateUserKeys();
  return {
    userId: id,
    keys,
    ecdhPub: await exportPublicRaw(keys.ecdh.publicKey),
    ecdsaPub: await exportPublicRaw(keys.ecdsa.publicKey),
    me: { userId: id, ecdhPriv: keys.ecdh.privateKey },
  };
}
const rcp = (u) => ({ userId: u.userId, ecdhPub: u.ecdhPub });

// realistic-ish plaintexts: text documents with repeated structure + random binary
function makeDoc(size) {
  const lines = [
    'EMPLOYEE_ID,NAME,DEPARTMENT,SALARY,BANK_ACCOUNT\n',
    'E1001,Aarav Sharma,Engineering,1450000,XXXX-XXXX-4421\n',
    'E1002,Diya Patel,Finance,1210000,XXXX-XXXX-9813\n',
    'E1003,Kabir Rao,Security,1380000,XXXX-XXXX-1177\n',
  ];
  let s = '';
  while (s.length < size) s += lines[s.length === 0 ? 0 : 1 + rnd(3)];
  return te.encode(s.slice(0, size));
}

const results = {
  meta: {
    date: new Date().toISOString(),
    node: process.version,
    openssl: process.versions.openssl,
    cpu: os.cpus()[0]?.model,
    cores: os.cpus().length,
    platform: `${os.type()} ${os.release()}`,
    quick: QUICK,
  },
};

// ---------------------------------------------------------------- E1 public-key decryption attack
async function e1() {
  log('E1 public-key attack');
  const N = QUICK ? 20 : 100;
  const alice = await mkUser('alice');
  const bob = await mkUser('bob');
  const base = baseKeygen();
  let baseOk = 0;
  let propOk = 0;
  let propTried = 0;
  for (let i = 0; i < N; i++) {
    const size = 1024 + rnd(64 * 1024);
    const plain = i % 2 ? makeDoc(size) : randomBytes(size);
    // base: attacker = anyone with the owner's public key + leaked ciphertext
    const ct = baseEncrypt(plain, base.pub);
    try {
      if (bytesEqual(publicKeyAttack(ct, base.pub), plain)) baseOk++;
    } catch {}
    // proposed: attacker has ciphertext + manifest + EVERY public key
    const p = await encryptFile(plain, { fileId: 'e1-' + i, ownerId: 'alice' }, [rcp(alice), rcp(bob)], alice.keys.ecdsa.privateKey);
    const r = await publicKeyAttackOnProposed(p.ciphertext, p.manifest, [alice.ecdhPub, bob.ecdhPub, alice.ecdsaPub, bob.ecdsaPub]);
    if (r.success) propOk++;
    propTried += r.tried;
  }
  results.e1_public_key_attack = {
    files: N,
    base_recovered: baseOk,
    proposed_recovered: propOk,
    proposed_candidate_keys_tried: propTried,
    note: 'attacker knows only public information (public keys + stored ciphertext/manifest)',
  };
}

// ---------------------------------------------------------------- E2 tampering by the cloud
async function e2() {
  log('E2 tampering');
  const T = QUICK ? 50 : 250;
  const alice = await mkUser('alice');
  const bob = await mkUser('bob');
  const base = baseKeygen();
  const kinds = ['bit_flip', 'block_swap', 'block_delete', 'splice_other_file', 'manifest_edit'];
  const out = {};
  for (const kind of kinds) {
    const r = { trials: T, base: { detected: 0, silent_corruption: 0 }, proposed: { detected: 0, silent_corruption: 0 } };
    for (let t = 0; t < T; t++) {
      const plain = makeDoc(4096 + 16 * rnd(256));
      const other = makeDoc(4096);
      // ---- base
      const bct = baseEncrypt(plain, base.pub);
      const bother = baseEncrypt(other, base.pub);
      let tb = bct.slice();
      const nb = Math.floor(bct.length / 16);
      if (kind === 'bit_flip') tb[rnd(tb.length)] ^= 1 << rnd(8);
      else if (kind === 'block_swap') {
        const i = rnd(nb - 1);
        let j = rnd(nb - 1);
        if (j === i) j = (i + 1) % (nb - 1);
        const bi = bct.slice(i * 16, i * 16 + 16);
        tb.set(bct.subarray(j * 16, j * 16 + 16), i * 16);
        tb.set(bi, j * 16);
      } else if (kind === 'block_delete') {
        const i = rnd(nb - 1);
        tb = new Uint8Array([...bct.subarray(0, i * 16), ...bct.subarray(i * 16 + 16)]);
      } else if (kind === 'splice_other_file') {
        const i = rnd(nb - 1);
        tb.set(bother.subarray(i * 16, i * 16 + 16), i * 16);
      } else if (kind === 'manifest_edit') {
        // base has no manifest: closest analogue = cloud swaps the whole file for another ciphertext of the same owner
        tb = bother.slice();
      }
      try {
        const o = baseDecrypt(tb, base.pub);
        if (bytesEqual(o, plain)) {
          /* no change */
        } else r.base.silent_corruption++;
      } catch {
        r.base.detected++;
      }
      // ---- proposed
      const p = await encryptFile(plain, { fileId: 'e2', ownerId: 'alice' }, [rcp(alice), rcp(bob)], alice.keys.ecdsa.privateKey);
      const po = await encryptFile(other, { fileId: 'e2-other', ownerId: 'alice' }, [rcp(alice), rcp(bob)], alice.keys.ecdsa.privateKey);
      let c = p.ciphertext.slice();
      let m = p.manifest;
      const n = Math.floor(c.length / 16);
      if (kind === 'bit_flip') c[rnd(c.length)] ^= 1 << rnd(8);
      else if (kind === 'block_swap') {
        const i = rnd(n - 1);
        let j = rnd(n - 1);
        if (j === i) j = (i + 1) % (n - 1);
        const bi = c.slice(i * 16, i * 16 + 16);
        c.set(p.ciphertext.subarray(j * 16, j * 16 + 16), i * 16);
        c.set(bi, j * 16);
      } else if (kind === 'block_delete') {
        const i = rnd(n - 1);
        c = new Uint8Array([...c.subarray(0, i * 16), ...c.subarray(i * 16 + 16)]);
      } else if (kind === 'splice_other_file') {
        const i = rnd(Math.min(n, Math.floor(po.ciphertext.length / 16)) - 1);
        c.set(po.ciphertext.subarray(i * 16, i * 16 + 16), i * 16);
      } else if (kind === 'manifest_edit') {
        const which = rnd(3);
        if (which === 0) m = { ...m, size: m.size - 16 };
        else if (which === 1) m = { ...m, recipients: m.recipients.filter((x) => x.userId !== 'bob') };
        else m = { ...m, ctHash: po.manifest.ctHash };
      }
      try {
        const o = await decryptFile(c, m, p.signature, bob.me, alice.ecdsaPub);
        if (!bytesEqual(o.plain, plain)) r.proposed.silent_corruption++;
      } catch (e) {
        r.proposed.detected++;
      }
    }
    out[kind] = r;
  }
  results.e2_tampering = out;
}

// ---------------------------------------------------------------- E3 ECB pattern leakage (image)
function readBmp(p) {
  const b = new Uint8Array(fs.readFileSync(p));
  const off = new DataView(b.buffer).getUint32(10, true);
  return { header: b.subarray(0, off), pixels: b.subarray(off) };
}
async function e3() {
  log('E3 ECB image leakage');
  const { header, pixels } = readBmp(path.join(HERE, 'data', 'sample_logo.bmp'));
  const base = baseKeygen();
  const alice = await mkUser('alice');
  const bct = baseEncrypt(pixels, base.pub).subarray(0, pixels.length);
  const p = await encryptFile(pixels, { fileId: 'img', ownerId: 'alice' }, [rcp(alice)], alice.keys.ecdsa.privateKey);
  const pct = p.ciphertext.subarray(0, pixels.length);
  fs.writeFileSync(path.join(OUT, 'ecb_original.bmp'), Buffer.concat([header, pixels]));
  fs.writeFileSync(path.join(OUT, 'ecb_base_encrypted.bmp'), Buffer.concat([header, bct]));
  fs.writeFileSync(path.join(OUT, 'ecb_proposed_encrypted.bmp'), Buffer.concat([header, pct]));
  const stat = (x) => ({ entropy_bits_per_byte: +shannonEntropy(x).toFixed(4), repeated_block_pct: +(100 * repeatedBlockRatio(x)).toFixed(2), chi_square: +chiSquare(x).toFixed(1) });
  results.e3_ecb_image = { bytes: pixels.length, original: stat(pixels), base: stat(bct), proposed: stat(pct) };
}

// ---------------------------------------------------------------- E4/E5 determinism + avalanche
async function e45() {
  log('E4/E5 determinism + avalanche');
  const R = QUICK ? 50 : 300;
  const base = baseKeygen();
  const alice = await mkUser('alice');
  const plain = makeDoc(4096);
  // E4 determinism: same file uploaded twice
  const b1 = baseEncrypt(plain, base.pub);
  const b2 = baseEncrypt(plain, base.pub);
  const p1 = await encryptFile(plain, { fileId: 'd', ownerId: 'alice' }, [rcp(alice)], alice.keys.ecdsa.privateKey);
  const p2 = await encryptFile(plain, { fileId: 'd', ownerId: 'alice' }, [rcp(alice)], alice.keys.ecdsa.privateKey);
  results.e4_determinism = {
    base_identical_ciphertexts: bytesEqual(b1, b2),
    base_bit_difference_pct: +(100 * bitDifference(b1, b2)).toFixed(2),
    proposed_identical_ciphertexts: bytesEqual(p1.ciphertext, p2.ciphertext),
    proposed_bit_difference_pct: +(100 * bitDifference(p1.ciphertext, p2.ciphertext)).toFixed(2),
  };
  // E5 avalanche: (a) 1-bit change in plaintext, whole 4 KiB file; (b) 1-bit change in AES key, single block
  const aBase = [];
  const aProp = [];
  const aKey = [];
  const aBlock = [];
  for (let r = 0; r < R; r++) {
    const pt = makeDoc(4096);
    const pt2 = pt.slice();
    pt2[rnd(pt2.length)] ^= 1 << rnd(8);
    aBase.push(bitDifference(baseEncrypt(pt, base.pub), baseEncrypt(pt2, base.pub)));
    const q1 = await encryptFile(pt, { fileId: 'a', ownerId: 'alice' }, [rcp(alice)], alice.keys.ecdsa.privateKey);
    const q2 = await encryptFile(pt2, { fileId: 'a', ownerId: 'alice' }, [rcp(alice)], alice.keys.ecdsa.privateKey);
    aProp.push(bitDifference(q1.ciphertext, q2.ciphertext));
    // AES primitive itself (what the paper measured): flip one key bit / one plaintext bit in one block
    const k = crypto.randomBytes(16);
    const k2 = Buffer.from(k);
    k2[rnd(16)] ^= 1 << rnd(8);
    const blk = crypto.randomBytes(16);
    const enc = (key, b) => {
      const c = crypto.createCipheriv('aes-128-ecb', key, null);
      c.setAutoPadding(false);
      return new Uint8Array(Buffer.concat([c.update(b), c.final()]));
    };
    aKey.push(bitDifference(enc(k, blk), enc(k2, blk)));
    const blk2 = Buffer.from(blk);
    blk2[rnd(16)] ^= 1 << rnd(8);
    aBlock.push(bitDifference(enc(k, blk), enc(k, blk2)));
  }
  const mean = (a) => a.reduce((x, y) => x + y, 0) / a.length;
  results.e5_avalanche = {
    trials: R,
    aes_block_1bit_key_change_pct: +(100 * mean(aKey)).toFixed(2),
    aes_block_1bit_plaintext_change_pct: +(100 * mean(aBlock)).toFixed(2),
    whole_file_4KiB_base_pct: +(100 * mean(aBase)).toFixed(2),
    whole_file_4KiB_proposed_pct: +(100 * mean(aProp)).toFixed(2),
    ideal_pct: 50,
    paper_reported: { proposed_key: 61, proposed_plaintext: 64, aes_key: 51, aes_plaintext: 55 },
  };
}

// ---------------------------------------------------------------- E6 performance vs file size
async function time(fn, reps) {
  await fn(); // warm-up (JIT, key import caches, allocator)
  const ts = [];
  for (let i = 0; i < reps; i++) {
    if (globalThis.gc) globalThis.gc(); // run with --expose-gc so GC pauses don't land inside a timing
    const t0 = performance.now();
    await fn();
    ts.push(performance.now() - t0);
  }
  return median(ts);
}
async function e6() {
  log('E6 performance');
  const sizes = QUICK ? [1, 64, 1024, 4096] : [1, 16, 256, 1024, 4096, 16384, 32768]; // KiB
  const alice = await mkUser('alice');
  const bob = await mkUser('bob');
  const base = baseKeygen();
  const rows = [];
  for (const kib of sizes) {
    const plain = randomBytes(kib * 1024);
    const reps = kib >= 16384 ? 7 : kib >= 1024 ? 11 : 25;
    const bEnc = await time(() => baseEncrypt(plain, base.pub), reps);
    const bct = baseEncrypt(plain, base.pub);
    const bDec = await time(() => baseDecrypt(bct, base.pub), reps);
    let last;
    const pEnc = await time(async () => {
      last = await encryptFile(plain, { fileId: 'perf', ownerId: 'alice' }, [rcp(alice), rcp(bob)], alice.keys.ecdsa.privateKey);
    }, reps);
    const pDec = await time(() => decryptFile(last.ciphertext, last.manifest, last.signature, bob.me, alice.ecdsaPub), reps);
    const mb = kib / 1024;
    rows.push({
      size_kib: kib,
      base_enc_ms: +bEnc.toFixed(3),
      base_dec_ms: +bDec.toFixed(3),
      proposed_enc_ms: +pEnc.toFixed(3),
      proposed_dec_ms: +pDec.toFixed(3),
      base_enc_mbps: +(mb / (bEnc / 1000)).toFixed(1),
      proposed_enc_mbps: +(mb / (pEnc / 1000)).toFixed(1),
      base_ct_overhead_bytes: bct.length - plain.length,
      proposed_ct_overhead_bytes: last.ciphertext.length - plain.length,
      proposed_manifest_bytes: JSON.stringify(last.manifest).length + last.signature.length,
    });
    log(`  ${kib} KiB  base ${bEnc.toFixed(2)} ms  proposed ${pEnc.toFixed(2)} ms`);
  }
  results.e6_performance = rows;
}

// ---------------------------------------------------------------- E7 sharing + E8 revocation
async function e78() {
  log('E7 sharing / E8 revocation');
  const alice = await mkUser('alice');
  const users = [];
  for (let i = 0; i < 100; i++) users.push(await mkUser('u' + String(i).padStart(3, '0')));
  const plain = randomBytes(1024 * 1024);
  const rows = [];
  for (const n of QUICK ? [1, 10, 50] : [1, 2, 5, 10, 25, 50, 100]) {
    const r = [rcp(alice), ...users.slice(0, n).map(rcp)];
    let last;
    const t = await time(async () => {
      last = await encryptFile(plain, { fileId: 'share', ownerId: 'alice' }, r, alice.keys.ecdsa.privateKey);
    }, 5);
    rows.push({ recipients: n, encrypt_and_share_ms: +t.toFixed(2), manifest_bytes: JSON.stringify(last.manifest).length });
  }
  // add one recipient later (no re-encryption)
  const p = await encryptFile(plain, { fileId: 'share', ownerId: 'alice' }, [rcp(alice)], alice.keys.ecdsa.privateKey);
  const addMs = await time(() => addRecipient(p.manifest, alice.me, rcp(users[0]), alice.keys.ecdsa.privateKey), 20);
  // revocation (re-key) vs file size
  const rev = [];
  for (const kib of QUICK ? [64, 1024] : [64, 1024, 4096, 16384]) {
    const pl = randomBytes(kib * 1024);
    const q = await encryptFile(pl, { fileId: 'rev', ownerId: 'alice' }, [rcp(alice), rcp(users[0]), rcp(users[1])], alice.keys.ecdsa.privateKey);
    const t = await time(() => rekeyFile(q.ciphertext, q.manifest, q.signature, alice.me, alice.ecdsaPub, [rcp(alice), rcp(users[1])], alice.keys.ecdsa.privateKey), 3);
    rev.push({ size_kib: kib, rekey_ms: +t.toFixed(2) });
  }
  results.e7_sharing = { file_kib: 1024, rows, add_recipient_later_ms: +addMs.toFixed(3) };
  results.e8_revocation = rev;
}

// ---------------------------------------------------------------- E9 primitive costs (ECC vs RSA)
async function e9() {
  log('E9 primitive costs');
  const subtle = globalThis.crypto.subtle;
  const ecKey = await time(() => subtle.generateKey({ name: 'ECDH', namedCurve: 'P-256' }, true, ['deriveBits']), 50);
  const a = await subtle.generateKey({ name: 'ECDH', namedCurve: 'P-256' }, true, ['deriveBits']);
  const b = await subtle.generateKey({ name: 'ECDH', namedCurve: 'P-256' }, true, ['deriveBits']);
  const ecdh = await time(() => subtle.deriveBits({ name: 'ECDH', public: b.publicKey }, a.privateKey, 256), 100);
  const s = await subtle.generateKey({ name: 'ECDSA', namedCurve: 'P-256' }, true, ['sign', 'verify']);
  const msg = randomBytes(256);
  const sig = await subtle.sign({ name: 'ECDSA', hash: 'SHA-256' }, s.privateKey, msg);
  const sign = await time(() => subtle.sign({ name: 'ECDSA', hash: 'SHA-256' }, s.privateKey, msg), 100);
  const verify = await time(() => subtle.verify({ name: 'ECDSA', hash: 'SHA-256' }, s.publicKey, sig, msg), 100);
  const rsaKey = await time(() => crypto.generateKeyPairSync('rsa', { modulusLength: 3072 }), QUICK ? 2 : 5);
  const { publicKey, privateKey } = crypto.generateKeyPairSync('rsa', { modulusLength: 3072 });
  const dek = randomBytes(32);
  const rsaWrap = await time(() => crypto.publicEncrypt({ key: publicKey, oaepHash: 'sha256' }, dek), 50);
  const w = crypto.publicEncrypt({ key: publicKey, oaepHash: 'sha256' }, dek);
  const rsaUnwrap = await time(() => crypto.privateDecrypt({ key: privateKey, oaepHash: 'sha256' }, w), 50);
  results.e9_primitives = {
    p256_keygen_ms: +ecKey.toFixed(3),
    p256_ecdh_ms: +ecdh.toFixed(3),
    p256_ecdsa_sign_ms: +sign.toFixed(3),
    p256_ecdsa_verify_ms: +verify.toFixed(3),
    rsa3072_keygen_ms: +rsaKey.toFixed(1),
    rsa3072_oaep_wrap_ms: +rsaWrap.toFixed(3),
    rsa3072_oaep_unwrap_ms: +rsaUnwrap.toFixed(3),
    key_bits: { p256_public: 256, rsa3072_public: 3072 },
  };
}

await e1();
await e2();
await e3();
await e45();
await e6();
await e78();
await e9();
fs.writeFileSync(path.join(OUT, 'results.json'), JSON.stringify(results, null, 2));
log('wrote', path.join(OUT, 'results.json'));
console.log(JSON.stringify({ e1: results.e1_public_key_attack, e3: results.e3_ecb_image, e4: results.e4_determinism, e5: results.e5_avalanche }, null, 1));
