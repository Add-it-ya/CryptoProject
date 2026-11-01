// =============================================================================================
// ATTACK LAB - the server plays the ATTACKER (outsider with a leaked storage dump, or a malicious
// cloud insider). Every route returns the attacker's steps with the real bytes involved.
// =============================================================================================
import { Router } from 'express';
import express from 'express';
import File from '../models/File.js';
import User from '../models/User.js';
import { requireAuth } from '../lib/auth.js';
import { emit } from '../lib/events.js';
import { ah, hex, ascii, stats } from '../lib/util.js';
import { getBlob, putBlob } from '../db.js';
import { deriveAesKeyFromPublic, baseDecrypt, baseEncrypt } from '@cryptovault/crypto-core/base';
import { publicKeyAttackOnProposed } from '@cryptovault/crypto-core/proposed';
import { fromB64 } from '@cryptovault/crypto-core/encoding';

const r = Router();
r.use(requireAuth);

const A = (title, values = {}) => ({ actor: 'attacker', title, values });

// ------------------------------------------------------------------ what the database really holds
r.get(
  '/dump',
  ah(async (req, res) => {
    const files = await File.find().sort({ createdAt: -1 }).limit(40);
    const out = [];
    for (const f of files) {
      const ct = await getBlob(f.gridId);
      out.push({
        id: String(f._id),
        scheme: f.scheme,
        ownerName: f.ownerName,
        storedName: f.scheme === 'base' ? f.name : '(encrypted in manifest)',
        size: f.size,
        storedSize: ct.length,
        first48: hex(ct, 48),
        ...stats(ct),
        version: f.version,
        recipients: f.scheme === 'proposed' ? f.manifest.recipients.length : f.sharedWith.length + 1,
        tampered: f.tampered,
      });
    }
    res.json(out);
  }),
);

// ------------------------------------------------------------------ ATTACK 1: public-key decryption
r.post(
  '/public-key-attack/:id',
  ah(async (req, res) => {
    const f = await File.findById(req.params.id);
    if (!f) return res.status(404).json({ error: 'not found' });
    const ct = await getBlob(f.gridId);
    const steps = [
      A('Attacker obtains the stored ciphertext (leaked backup / misconfigured bucket / insider)', {
        file: f.scheme === 'base' ? f.name : `fileId ${f.fileId}`,
        'ciphertext bytes': hex(ct, 24),
        'attacker has any private key?': 'NO',
      }),
    ];
    const owner = await User.findById(f.owner);
    let success = false;
    let preview = null;
    if (f.scheme === 'base') {
      const pub = fromB64(owner.basePub);
      steps.push(A(`Attacker downloads ${owner.username}'s PUBLIC key from the public directory`, { 'public key P': hex(pub, 24) }));
      const key = deriveAesKeyFromPublic(pub, 128);
      steps.push(A('Attacker applies the paper\'s own rule: AES key = f(public key)', { 'AES-128 key = SHA-256(P.x)[0:16]': hex(key) }));
      try {
        const pt = baseDecrypt(ct, pub);
        success = true;
        const isText = !f.mime || f.mime.startsWith('text') || f.mime.includes('csv') || f.mime.includes('json');
        preview = { text: isText ? Buffer.from(pt.subarray(0, 600)).toString('utf8') : ascii(pt, 400), b64: f.mime?.startsWith('image/') ? Buffer.from(pt).toString('base64') : null, mime: f.mime };
        steps.push(A('AES-ECB decrypt with the derived key -> FULL PLAINTEXT RECOVERED', { 'recovered plaintext': ascii(pt, 80) }));
      } catch (e) {
        steps.push(A('decrypt failed', { error: String(e.message) }));
      }
    } else {
      const users = await User.find();
      const pubs = [];
      for (const u of users) pubs.push(fromB64(u.ecdhPub), fromB64(u.ecdsaPub), fromB64(u.basePub));
      steps.push(
        A(`Attacker downloads ALL ${pubs.length} public keys in the directory + the full manifest`, {
          'manifest fields': Object.keys(f.manifest).join(', '),
          'locked keys in manifest': String(f.manifest.recipients.length),
        }),
      );
      const t0 = performance.now();
      const r2 = await publicKeyAttackOnProposed(ct, f.manifest, pubs);
      success = r2.success;
      steps.push(
        A(`Tried ${r2.tried} candidate keys derived from every public value -> ${success ? 'SUCCESS' : 'ALL FAILED'}`, {
          'AES-GCM tag checks passed': success ? '1' : '0',
          why: 'the DEK is 256 random bits; it exists only inside the locked (ECDH-wrapped) keys',
          'brute force instead?': '2^256 keys -> infeasible',
          'time spent': `${(performance.now() - t0).toFixed(1)} ms`,
        }),
      );
    }
    for (const st of steps) emit({ ...st, user: req.user.username, route: 'POST /api/lab/public-key-attack' });
    res.json({ scheme: f.scheme, success, preview, steps });
  }),
);

// ------------------------------------------------------------------ ATTACK 2: insider tampering
r.post(
  '/tamper/:id',
  ah(async (req, res) => {
    const f = await File.findById(req.params.id);
    if (!f) return res.status(404).json({ error: 'not found' });
    const kind = req.body.kind || 'block_swap';
    const ct = await getBlob(f.gridId);
    if (!f.backupGridId) f.backupGridId = await putBlob(ct, 'backup-' + f._id, { backup: true });
    const t = ct.slice();
    const nb = Math.floor(t.length / 16);
    let values = {};
    if (kind === 'bit_flip') {
      const off = Math.min(20, t.length - 1);
      const before = t[off];
      t[off] ^= 0x01;
      values = { 'byte offset': String(off), before: before.toString(16).padStart(2, '0'), after: t[off].toString(16).padStart(2, '0'), 'bits changed': '1' };
    } else if (kind === 'block_swap') {
      const i = Math.min(2, nb - 2);
      const j = Math.min(4, nb - 1);
      const bi = t.slice(i * 16, i * 16 + 16);
      const bj = t.slice(j * 16, j * 16 + 16);
      t.set(bj, i * 16);
      t.set(bi, j * 16);
      values = { [`block ${i} (before)`]: hex(bi), [`block ${j} (before)`]: hex(bj), action: `swapped ciphertext blocks ${i} <-> ${j}` };
    } else if (kind === 'delete_block') {
      const i = Math.min(1, nb - 1);
      values = { [`deleted block ${i}`]: hex(t.subarray(i * 16, i * 16 + 16)) };
      const t2 = new Uint8Array(t.length - 16);
      t2.set(t.subarray(0, i * 16));
      t2.set(t.subarray(i * 16 + 16), i * 16);
      f.tampered = kind;
      f.gridId = await putBlob(t2, 'tampered-' + f._id);
      await f.save();
      const steps = [A('Malicious cloud insider deletes one 16-byte block of the stored ciphertext', values)];
      for (const st of steps) emit({ ...st, user: req.user.username, route: 'POST /api/lab/tamper' });
      return res.json({ ok: true, steps });
    }
    f.tampered = kind;
    f.gridId = await putBlob(t, 'tampered-' + f._id);
    await f.save();
    const steps = [
      A(`Malicious cloud insider modifies the stored ciphertext (${kind.replace('_', ' ')})`, {
        ...values,
        'needs any key?': 'NO - just edits bytes on disk',
        'next step': 'now download the file as a normal user and see what happens',
      }),
    ];
    for (const st of steps) emit({ ...st, user: req.user.username, route: 'POST /api/lab/tamper' });
    res.json({ ok: true, steps });
  }),
);

r.post(
  '/restore/:id',
  ah(async (req, res) => {
    const f = await File.findById(req.params.id);
    if (!f || !f.backupGridId) return res.json({ ok: true });
    f.gridId = f.backupGridId;
    f.backupGridId = null;
    f.tampered = null;
    await f.save();
    emit({ user: req.user.username, route: 'POST /api/lab/restore', title: 'Original ciphertext restored from backup' });
    res.json({ ok: true });
  }),
);

// ------------------------------------------------------------------ ATTACK 3: ECB pattern leakage
// The browser sends raw RGBA pixels; the server encrypts them with the BASE scheme (AES-ECB, the
// user's public-key-derived key) and returns the ciphertext bytes, which the browser draws as pixels.
r.post(
  '/ecb',
  express.raw({ type: 'application/octet-stream', limit: '32mb' }),
  ah(async (req, res) => {
    const px = new Uint8Array(req.body);
    const ct = baseEncrypt(px, fromB64(req.user.basePub)).subarray(0, px.length);
    const s0 = stats(px);
    const s1 = stats(ct);
    emit({
      user: req.user.username,
      route: 'POST /api/lab/ecb',
      title: 'Encrypted image pixels with the BASE scheme (AES-ECB)',
      values: {
        'pixel bytes': String(px.length),
        'plaintext repeated blocks': `${s0.repeatedBlocksPct}%`,
        'ciphertext repeated blocks': `${s1.repeatedBlocksPct}% (same pattern survives encryption)`,
        'ciphertext entropy': `${s1.entropy} bits/byte`,
      },
    });
    res.set('X-Stats', JSON.stringify({ plain: s0, base: s1 }));
    res.set('Access-Control-Expose-Headers', 'X-Stats');
    res.type('application/octet-stream').send(Buffer.from(ct));
  }),
);

export default r;
