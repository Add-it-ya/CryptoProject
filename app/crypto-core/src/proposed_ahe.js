// ---------------------------------------------------------------------------------------------
// PROPOSED SCHEME  -  AHE-v1 "Authenticated Hybrid Envelope"  (Group 18)
//
// Fixes the three weaknesses of the base AES-ECC model:
//   W1  key derived from the PUBLIC key       -> fresh random 256-bit DEK per file (CSPRNG), never
//                                                derivable from public data; DEK is *wrapped* for each
//                                                recipient with ECIES-style ECDH(P-256) + HKDF-SHA256.
//   W2  no integrity / authentication, ECB     -> AES-256-GCM (CTR mode + GHASH over GF(2^128)) on
//                                                1 MiB chunks, nonce = prefix||counter, AAD binds
//                                                fileId | version | chunk index | last-chunk flag
//                                                (blocks re-ordering, truncation, cross-file splicing);
//                                                manifest signed by the owner with ECDSA P-256/SHA-256.
//   W3  CSP holds keys / no sharing model      -> end-to-end (client-side) encryption, zero-knowledge
//                                                server; per-recipient key wrapping; revocation by
//                                                re-keying (new DEK + new version).
//
// Everything here uses only the standard WebCrypto API, so the *same file* runs in the React client
// (browser) and in Node (seed script, benchmarks, tests).
// ---------------------------------------------------------------------------------------------
import { te, td, concatBytes, u32be, toB64, fromB64, toHex, randomBytes, canonicalJSON, sha256 } from './encoding.js';

const subtle = globalThis.crypto.subtle;
export const SCHEME = 'AHE-v1';
export const CHUNK_SIZE = 1 << 20; // 1 MiB plaintext per GCM segment
export const TAG_BYTES = 16;
export const PBKDF2_ITER = 600_000; // OWASP 2023 recommendation for PBKDF2-HMAC-SHA256

export class IntegrityError extends Error {
  constructor(stage, msg) {
    super(msg || `Integrity check failed at: ${stage}`);
    this.name = 'IntegrityError';
    this.stage = stage;
  }
}
export class AccessError extends Error {
  constructor(msg) {
    super(msg);
    this.name = 'AccessError';
  }
}

// ----------------------------------------------------------------------------- user key material
/** Two independent P-256 key pairs: one for key agreement (ECDH), one for signatures (ECDSA). */
export async function generateUserKeys() {
  const ecdh = await subtle.generateKey({ name: 'ECDH', namedCurve: 'P-256' }, true, ['deriveBits']);
  const ecdsa = await subtle.generateKey({ name: 'ECDSA', namedCurve: 'P-256' }, true, ['sign', 'verify']);
  return { ecdh, ecdsa };
}

export async function exportPublicRaw(key) {
  return new Uint8Array(await subtle.exportKey('raw', key));
}
export function importEcdhPublic(raw) {
  return subtle.importKey('raw', raw, { name: 'ECDH', namedCurve: 'P-256' }, true, []);
}
export function importEcdsaPublic(raw) {
  return subtle.importKey('raw', raw, { name: 'ECDSA', namedCurve: 'P-256' }, true, ['verify']);
}

/**
 * Password-derived values. The server only ever receives `authToken`; the private keys are sealed
 * with a *different* key (random salt, 600k PBKDF2 iterations) so the server cannot open the vault.
 */
export async function deriveAuthToken(username, password, iterations = 100_000) {
  const base = await subtle.importKey('raw', te.encode(password), 'PBKDF2', false, ['deriveBits']);
  const bits = await subtle.deriveBits(
    { name: 'PBKDF2', hash: 'SHA-256', salt: te.encode('cryptovault-auth:' + username.toLowerCase()), iterations },
    base,
    256,
  );
  return toHex(new Uint8Array(bits));
}

async function vaultKey(password, salt, iterations) {
  const base = await subtle.importKey('raw', te.encode(password), 'PBKDF2', false, ['deriveKey']);
  return subtle.deriveKey(
    { name: 'PBKDF2', hash: 'SHA-256', salt, iterations },
    base,
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt', 'decrypt'],
  );
}

export async function sealPrivateKeys(keys, password, iterations = PBKDF2_ITER) {
  const payload = te.encode(
    JSON.stringify({
      ecdh: toB64(new Uint8Array(await subtle.exportKey('pkcs8', keys.ecdh.privateKey))),
      ecdsa: toB64(new Uint8Array(await subtle.exportKey('pkcs8', keys.ecdsa.privateKey))),
    }),
  );
  const salt = randomBytes(16);
  const iv = randomBytes(12);
  const k = await vaultKey(password, salt, iterations);
  const ct = new Uint8Array(await subtle.encrypt({ name: 'AES-GCM', iv, additionalData: te.encode('vault') }, k, payload));
  payload.fill(0);
  return { kdf: 'PBKDF2-SHA256', iter: iterations, salt: toB64(salt), iv: toB64(iv), ct: toB64(ct) };
}

export async function openPrivateKeys(vault, password) {
  const k = await vaultKey(password, fromB64(vault.salt), vault.iter);
  let pt;
  try {
    pt = await subtle.decrypt({ name: 'AES-GCM', iv: fromB64(vault.iv), additionalData: te.encode('vault') }, k, fromB64(vault.ct));
  } catch {
    throw new AccessError('Wrong password (key vault authentication tag mismatch)');
  }
  const j = JSON.parse(td.decode(pt));
  const ecdhPriv = await subtle.importKey('pkcs8', fromB64(j.ecdh), { name: 'ECDH', namedCurve: 'P-256' }, false, ['deriveBits']);
  const ecdsaPriv = await subtle.importKey('pkcs8', fromB64(j.ecdsa), { name: 'ECDSA', namedCurve: 'P-256' }, false, ['sign']);
  return { ecdhPriv, ecdsaPriv };
}

// ----------------------------------------------------------------------------- key wrapping (ECIES)
function wrapInfo(fileId, version, userId, ephRaw) {
  return concatBytes(te.encode(`${SCHEME}/wrap|${fileId}|v${version}|${userId}|`), ephRaw);
}
function wrapAad(fileId, version, userId) {
  return te.encode(`${SCHEME}/dek|${fileId}|v${version}|${userId}`);
}

async function kekFromShared(sharedBits, fileId, info) {
  const ikm = await subtle.importKey('raw', sharedBits, 'HKDF', false, ['deriveKey']);
  return subtle.deriveKey(
    { name: 'HKDF', hash: 'SHA-256', salt: te.encode(fileId), info },
    ikm,
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt', 'decrypt'],
  );
}

/** ECIES-KEM: ephemeral ECDH with the recipient's public key -> HKDF -> AES-GCM wrap of the DEK. */
export async function wrapDek(dek, recipientId, recipientEcdhPubRaw, fileId, version, trace, label) {
  const t0 = now();
  const recipientPub = await importEcdhPublic(recipientEcdhPubRaw);
  const eph = await subtle.generateKey({ name: 'ECDH', namedCurve: 'P-256' }, true, ['deriveBits']);
  const ephRaw = await exportPublicRaw(eph.publicKey);
  const shared = new Uint8Array(await subtle.deriveBits({ name: 'ECDH', public: recipientPub }, eph.privateKey, 256));
  const kek = await kekFromShared(shared, fileId, wrapInfo(fileId, version, recipientId, ephRaw));
  const kekPreview = trace ? await sha256(shared) : null;
  const iv = randomBytes(12);
  const wrapped = new Uint8Array(
    await subtle.encrypt({ name: 'AES-GCM', iv, additionalData: wrapAad(fileId, version, recipientId) }, kek, dek),
  );
  emit(trace, 'client', `Lock the file key for ${label || recipientId} (ECDH + HKDF + AES-GCM key-wrap)`, {
    'recipient public key Q': hx(recipientEcdhPubRaw, 20),
    'ephemeral secret r': '(random, used once, then discarded)',
    'ephemeral public R = r·G': hx(ephRaw, 20),
    'shared secret S = r·Q  (ECDH)': hx(shared),
    'KEK = HKDF-SHA256(S)': '(non-extractable CryptoKey) fingerprint ' + hx(kekPreview, 8),
    'wrapped DEK (32 B key + 16 B tag)': hx(wrapped, 48),
  }, t0);
  shared.fill(0);
  return { userId: recipientId, eph: toB64(ephRaw), iv: toB64(iv), wrapped: toB64(wrapped) };
}

export async function unwrapDek(entry, myEcdhPriv, fileId, version, trace) {
  const t0 = now();
  const ephRaw = fromB64(entry.eph);
  const ephPub = await importEcdhPublic(ephRaw);
  const shared = new Uint8Array(await subtle.deriveBits({ name: 'ECDH', public: ephPub }, myEcdhPriv, 256));
  const kek = await kekFromShared(shared, fileId, wrapInfo(fileId, version, entry.userId, ephRaw));
  let dek;
  try {
    dek = new Uint8Array(
      await subtle.decrypt(
        { name: 'AES-GCM', iv: fromB64(entry.iv), additionalData: wrapAad(fileId, version, entry.userId) },
        kek,
        fromB64(entry.wrapped),
      ),
    );
  } catch {
    emit(trace, 'client', 'Unlock file key FAILED (key-wrap tag mismatch)', { 'shared secret S = d·R': hx(shared) }, t0);
    throw new AccessError('Cannot unwrap the file key with this private key');
  }
  emit(trace, 'client', 'Unlock the file key with MY private key (ECDH: S = d·R, same S as sender)', {
    'ephemeral public R (from manifest)': hx(ephRaw, 20),
    'shared secret S = d·R': hx(shared),
    'recovered DEK (AES-256 key)': hx(dek),
  }, t0);
  shared.fill(0);
  return dek;
}

// ----------------------------------------------------------------------------- file encryption
function chunkNonce(prefix, i) {
  return concatBytes(prefix, u32be(i));
}
function chunkAad(fileId, version, i, last) {
  return te.encode(`${SCHEME}/chunk|${fileId}|v${version}|${i}|${last ? 1 : 0}`);
}
const META_INDEX = 0xffffffff;

// ----------------------------------------------------------------------------- tracing (demo)
// Every public function accepts an optional `trace` callback. The demo UI ("Crypto Inspector")
// renders each event live so the audience can SEE the real intermediate values.
const now = () => (globalThis.performance ? performance.now() : Date.now());
const hx = (b, n = 32) => {
  const h = toHex(b instanceof Uint8Array ? b : new Uint8Array(b));
  return h.length > n * 2 ? h.slice(0, n * 2) + `… (${b.byteLength} B)` : h;
};
function emit(trace, actor, title, values = {}, t0) {
  if (!trace) return;
  trace({ actor, title, values, ms: t0 != null ? +(now() - t0).toFixed(3) : undefined, at: Date.now() });
}
export { hx };

async function importDek(dek) {
  return subtle.importKey('raw', dek, { name: 'AES-GCM' }, false, ['encrypt', 'decrypt']);
}

async function signManifest(manifest, ownerSignPriv) {
  const sig = await subtle.sign({ name: 'ECDSA', hash: 'SHA-256' }, ownerSignPriv, te.encode(canonicalJSON(manifest)));
  return toB64(new Uint8Array(sig));
}

export async function verifyManifest(manifest, signatureB64, ownerSignPubRaw) {
  const pub = await importEcdsaPublic(ownerSignPubRaw);
  return subtle.verify({ name: 'ECDSA', hash: 'SHA-256' }, pub, fromB64(signatureB64), te.encode(canonicalJSON(manifest)));
}

/**
 * Encrypt + share in one step.
 * @param {Uint8Array} plain           file bytes
 * @param {object} info                { fileId, ownerId, version, name, mime }
 * @param {Array} recipients           [{ userId, ecdhPub (Uint8Array raw) }]  (include the owner!)
 * @param {CryptoKey} ownerSignPriv    owner's ECDSA private key
 * @param {Uint8Array} [dekIn]         optional existing DEK (only used by tests)
 */
export async function encryptFile(plain, info, recipients, ownerSignPriv, dekIn, trace) {
  const { fileId, ownerId, version = 1, name = 'file', mime = 'application/octet-stream' } = info;
  let t0 = now();
  const dek = dekIn || randomBytes(32);
  const key = await importDek(dek);
  const prefix = randomBytes(8);
  emit(trace, 'client', 'Generate a fresh random file key (DEK) with the browser CSPRNG', {
    'DEK (256-bit AES key)': hx(dek),
    'nonce prefix (64 bit)': hx(prefix),
    'derived from public data?': 'NO - pure randomness, 256 bits of entropy',
  }, t0);
  const n = Math.max(1, Math.ceil(plain.length / CHUNK_SIZE));
  const parts = [];
  t0 = now();
  for (let i = 0; i < n; i++) {
    const chunk = plain.subarray(i * CHUNK_SIZE, Math.min(plain.length, (i + 1) * CHUNK_SIZE));
    const ct = await subtle.encrypt(
      { name: 'AES-GCM', iv: chunkNonce(prefix, i), additionalData: chunkAad(fileId, version, i, i === n - 1), tagLength: 128 },
      key,
      chunk,
    );
    parts.push(new Uint8Array(ct));
  }
  const ciphertext = concatBytes(...parts);
  const first = parts[0];
  emit(trace, 'client', `Encrypt + authenticate with AES-256-GCM (${n} chunk${n > 1 ? 's' : ''})`, {
    'plaintext (first bytes)': hx(plain.subarray(0, 24), 24),
    'nonce for chunk 0': hx(chunkNonce(prefix, 0)),
    'associated data (bound, not secret)': td.decode(chunkAad(fileId, version, 0, n === 1)),
    'ciphertext (first bytes)': hx(first.subarray(0, 24), 24),
    'GCM auth tag of chunk 0 (16 B)': hx(first.subarray(first.length - TAG_BYTES)),
    'size plaintext -> ciphertext': `${plain.length} B -> ${ciphertext.length} B (+${n * TAG_BYTES} B tags)`,
  }, t0);
  // file name + MIME type are confidential too (the base scheme leaks them to the CSP)
  const encMeta = new Uint8Array(
    await subtle.encrypt(
      { name: 'AES-GCM', iv: chunkNonce(prefix, META_INDEX), additionalData: te.encode(`${SCHEME}/meta|${fileId}|v${version}`) },
      key,
      te.encode(JSON.stringify({ name, mime })),
    ),
  );
  const wraps = [];
  for (const r of recipients) wraps.push(await wrapDek(dek, r.userId, r.ecdhPub, fileId, version, trace, r.label));
  wraps.sort((a, b) => (a.userId < b.userId ? -1 : 1));
  t0 = now();
  const ctHashBytes = await sha256(ciphertext);
  const manifest = {
    scheme: SCHEME,
    aead: 'AES-256-GCM',
    kem: 'ECDH-P256+HKDF-SHA256',
    sig: 'ECDSA-P256-SHA256',
    fileId,
    ownerId,
    version,
    size: plain.length,
    chunkSize: CHUNK_SIZE,
    chunks: n,
    noncePrefix: toB64(prefix),
    encMeta: toB64(encMeta),
    ctHash: toHex(ctHashBytes),
    recipients: wraps,
  };
  const signature = await signManifest(manifest, ownerSignPriv);
  emit(trace, 'client', 'Sign the manifest with my ECDSA private key (proves who uploaded it, detects any change)', {
    'SHA-256(ciphertext)': hx(ctHashBytes),
    'manifest fields signed': Object.keys(manifest).join(', '),
    'ECDSA-P256 signature (r||s, 64 B)': hx(fromB64(signature), 64),
  }, t0);
  if (!dekIn) dek.fill(0);
  emit(trace, 'client', 'DEK wiped from memory - only ciphertext + locked keys leave the browser', {
    'sent to cloud': `ciphertext (${ciphertext.length} B), manifest, signature`,
    'NOT sent to cloud': 'plaintext, file name, DEK, any private key',
  });
  return { ciphertext, manifest, signature };
}

/**
 * Verify-then-decrypt. Throws IntegrityError (tampering) or AccessError (not a recipient).
 * Order: ECDSA signature -> SHA-256 of ciphertext -> unwrap DEK -> GCM tag of every chunk.
 */
export async function decryptFile(ciphertext, manifest, signature, me, ownerSignPubRaw, trace) {
  let t0 = now();
  const sigOk = await verifyManifest(manifest, signature, ownerSignPubRaw);
  emit(trace, 'client', `Step 1 - verify owner's ECDSA signature: ${sigOk ? 'VALID' : 'INVALID'}`, {
    'owner signing public key': hx(ownerSignPubRaw, 20),
    signature: hx(fromB64(signature), 64),
    result: sigOk ? 'manifest is exactly what the owner signed' : 'manifest was modified -> STOP',
  }, t0);
  if (!sigOk) throw new IntegrityError('signature', 'Owner signature on manifest is INVALID');
  t0 = now();
  const h = await sha256(ciphertext);
  const hashOk = toHex(h) === manifest.ctHash;
  emit(trace, 'client', `Step 2 - SHA-256 of downloaded ciphertext ${hashOk ? 'matches' : 'DOES NOT match'} the signed hash`, {
    'SHA-256(downloaded ciphertext)': hx(h),
    'hash inside signed manifest': manifest.ctHash.slice(0, 64),
    result: hashOk ? 'cloud returned the untouched ciphertext' : 'ciphertext was modified in the cloud -> STOP',
  }, t0);
  if (!hashOk) throw new IntegrityError('hash', 'Ciphertext hash does not match signed manifest');
  const entry = manifest.recipients.find((r) => r.userId === me.userId);
  if (!entry) {
    emit(trace, 'client', 'Step 3 - no locked key for me in this version', { result: 'access revoked or never shared' });
    throw new AccessError('You are not (or no longer) a recipient of this file version');
  }
  const dek = await unwrapDek(entry, me.ecdhPriv, manifest.fileId, manifest.version, trace);
  const key = await importDek(dek);
  dek.fill(0);
  const prefix = fromB64(manifest.noncePrefix);
  const n = manifest.chunks;
  const segLen = manifest.chunkSize + TAG_BYTES;
  if (ciphertext.length !== manifest.size + n * TAG_BYTES) throw new IntegrityError('length', 'Ciphertext length mismatch (truncation/extension)');
  const out = new Uint8Array(manifest.size);
  t0 = now();
  for (let i = 0; i < n; i++) {
    const seg = ciphertext.subarray(i * segLen, Math.min(ciphertext.length, (i + 1) * segLen));
    let pt;
    try {
      pt = await subtle.decrypt(
        { name: 'AES-GCM', iv: chunkNonce(prefix, i), additionalData: chunkAad(manifest.fileId, manifest.version, i, i === n - 1), tagLength: 128 },
        key,
        seg,
      );
    } catch {
      emit(trace, 'client', `AES-GCM tag check FAILED in chunk ${i}`, { result: 'refusing to output tampered data' }, t0);
      throw new IntegrityError('gcm-tag', `GCM authentication tag mismatch in chunk ${i}`);
    }
    out.set(new Uint8Array(pt), i * manifest.chunkSize);
  }
  emit(trace, 'client', `Step 4 - AES-256-GCM decrypt: all ${n} tag check(s) passed`, {
    'recovered plaintext (first bytes)': hx(out.subarray(0, 24), 24),
    'plaintext size': `${out.length} B`,
  }, t0);
  const meta = JSON.parse(
    td.decode(
      await subtle.decrypt(
        { name: 'AES-GCM', iv: chunkNonce(prefix, META_INDEX), additionalData: te.encode(`${SCHEME}/meta|${manifest.fileId}|v${manifest.version}`) },
        key,
        fromB64(manifest.encMeta),
      ),
    ),
  );
  return { plain: out, meta };
}

/** Decrypt only the (encrypted) file name + MIME type, for listing files in the UI. */
export async function decryptMeta(manifest, me) {
  const entry = manifest.recipients.find((r) => r.userId === me.userId);
  if (!entry) return null;
  const dek = await unwrapDek(entry, me.ecdhPriv, manifest.fileId, manifest.version);
  const key = await importDek(dek);
  dek.fill(0);
  const prefix = fromB64(manifest.noncePrefix);
  const pt = await subtle.decrypt(
    { name: 'AES-GCM', iv: chunkNonce(prefix, META_INDEX), additionalData: te.encode(`${SCHEME}/meta|${manifest.fileId}|v${manifest.version}`) },
    key,
    fromB64(manifest.encMeta),
  );
  return JSON.parse(td.decode(pt));
}

/**
 * Share with one more user WITHOUT re-encrypting the file: owner unwraps its own DEK copy, wraps it
 * for the new recipient, and re-signs the manifest. Cost: one ECDH + one ECDSA sign (~ms).
 */
export async function addRecipient(manifest, owner, newRecipient, ownerSignPriv, trace) {
  const own = manifest.recipients.find((r) => r.userId === owner.userId);
  if (!own) throw new AccessError('Owner wrap entry missing');
  const dek = await unwrapDek(own, owner.ecdhPriv, manifest.fileId, manifest.version, trace);
  const w = await wrapDek(dek, newRecipient.userId, newRecipient.ecdhPub, manifest.fileId, manifest.version, trace, newRecipient.label);
  dek.fill(0);
  const recipients = manifest.recipients.filter((r) => r.userId !== newRecipient.userId).concat([w]);
  recipients.sort((a, b) => (a.userId < b.userId ? -1 : 1));
  const m2 = { ...manifest, recipients };
  const t0 = now();
  const signature = await signManifest(m2, ownerSignPriv);
  emit(trace, 'client', 'Re-sign manifest (file itself is NOT re-encrypted - only a 48-byte locked key is added)', {
    'new signature': hx(fromB64(signature), 64),
    recipients: String(recipients.length),
  }, t0);
  return { manifest: m2, signature };
}

/**
 * Revocation by re-keying: decrypt, then re-encrypt under a NEW random DEK as version+1 and wrap it
 * only for the remaining recipients. A revoked user's old wrapped key opens nothing new.
 */
export async function rekeyFile(ciphertext, manifest, signature, owner, ownerSignPubRaw, remaining, ownerSignPriv, trace) {
  const { plain, meta } = await decryptFile(ciphertext, manifest, signature, owner, ownerSignPubRaw, trace);
  emit(trace, 'client', `Revocation: re-key to version ${manifest.version + 1} with a NEW random DEK`, {
    'remaining recipients': remaining.map((r) => r.label || r.userId).join(', '),
    why: 'the revoked user still holds the OLD DEK, so the content must move to a new key',
  });
  const res = await encryptFile(
    plain,
    { fileId: manifest.fileId, ownerId: manifest.ownerId, version: manifest.version + 1, name: meta.name, mime: meta.mime },
    remaining,
    ownerSignPriv,
    undefined,
    trace,
  );
  plain.fill(0);
  return res;
}

/**
 * ATTACK 1 against the proposed scheme: the attacker has the ciphertext, the full manifest and EVERY
 * public key in the directory, and tries the base paper's trick (derive the AES key from public data).
 * Returns { success:false, tried:[...] } - there is no public value from which the DEK follows.
 */
export async function publicKeyAttackOnProposed(ciphertext, manifest, publicKeysRaw) {
  const tried = [];
  const prefix = fromB64(manifest.noncePrefix);
  const candidates = [];
  for (const pk of publicKeysRaw) {
    candidates.push(await sha256(pk.subarray(1, 33))); // base-paper derivation: SHA-256(P.x)
    candidates.push(await sha256(pk));
  }
  for (const w of manifest.recipients) candidates.push(await sha256(fromB64(w.eph)));
  const seg = ciphertext.subarray(0, Math.min(ciphertext.length, manifest.chunkSize + TAG_BYTES));
  for (const cand of candidates) {
    const key = await importDek(cand);
    try {
      await subtle.decrypt(
        { name: 'AES-GCM', iv: chunkNonce(prefix, 0), additionalData: chunkAad(manifest.fileId, manifest.version, 0, manifest.chunks === 1) },
        key,
        seg,
      );
      return { success: true, tried: tried.length + 1 };
    } catch {
      tried.push(toHex(cand).slice(0, 12));
    }
  }
  return { success: false, tried: tried.length };
}
