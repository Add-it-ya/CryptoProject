import { Router } from 'express';
import multer from 'multer';
import mongoose from 'mongoose';
import File from '../models/File.js';
import User from '../models/User.js';
import { requireAuth } from '../lib/auth.js';
import { emit } from '../lib/events.js';
import { ah, hex, ascii, stats } from '../lib/util.js';
import { putBlob, getBlob, deleteBlob } from '../db.js';
import { baseEncryptTraced, baseDecryptTraced } from '@cryptovault/crypto-core/base';
import { fromB64 } from '@cryptovault/crypto-core/encoding';

const upload = multer({ storage: multer.memoryStorage(), limits: { fileSize: 64 * 1024 * 1024 } });
const r = Router();
r.use(requireAuth);

const isId = (s) => mongoose.isValidObjectId(s);
const canRead = (f, u) => String(f.owner) === String(u._id) || f.sharedWith.some((x) => String(x) === String(u._id));
const wasRecipient = (f, u) => (f.revoked || []).some((x) => String(x) === String(u._id));

function view(f) {
  return {
    id: String(f._id),
    scheme: f.scheme,
    owner: String(f.owner),
    ownerName: f.ownerName,
    name: f.name,
    mime: f.mime,
    size: f.size,
    storedSize: f.storedSize,
    sharedWith: f.sharedWith.map(String),
    revoked: (f.revoked || []).map(String),
    fileId: f.fileId,
    manifest: f.manifest,
    signature: f.signature,
    version: f.version,
    tampered: f.tampered,
    createdAt: f.createdAt,
  };
}

// ------------------------------------------------------------------------------------ list
r.get(
  '/',
  ah(async (req, res) => {
    const files = await File.find({ $or: [{ owner: req.user._id }, { sharedWith: req.user._id }, { revoked: req.user._id }] }).sort({ createdAt: -1 });
    res.json(files.map(view));
  }),
);

// ------------------------------------------------------------------------------------ BASE upload
// Paper (Fig. 3/5): user -> CSP -> verification -> encryption -> cloud server.
// So the browser sends the PLAINTEXT file and the server encrypts it.
r.post(
  '/base',
  upload.single('file'),
  ah(async (req, res) => {
    if (!req.file) return res.status(400).json({ error: 'file missing' });
    const plain = new Uint8Array(req.file.buffer);
    const recipients = JSON.parse(req.body.recipients || '[]').filter(isId);
    const steps = [];
    steps.push({
      actor: 'server',
      title: 'CSP received the PLAINTEXT file over the network ("verification" = login token check)',
      values: {
        'file name (visible to CSP)': req.file.originalname,
        'plaintext as text': ascii(plain, 60),
        'plaintext bytes': hex(plain, 24),
        'Shannon entropy': `${stats(plain).entropy} bits/byte`,
      },
    });
    const pub = fromB64(req.user.basePub);
    const { ciphertext, steps: encSteps } = baseEncryptTraced(plain, pub);
    steps.push(...encSteps);
    const gridId = await putBlob(ciphertext, 'base-' + req.file.originalname, { scheme: 'base' });
    const f = await File.create({
      scheme: 'base',
      owner: req.user._id,
      ownerName: req.user.username,
      name: req.file.originalname,
      mime: req.file.mimetype,
      size: plain.length,
      storedSize: ciphertext.length,
      gridId,
      sharedWith: recipients,
    });
    const s = stats(ciphertext);
    steps.push({
      actor: 'server',
      title: 'Stored in MongoDB GridFS',
      values: {
        'GridFS id': String(gridId),
        'stored bytes': hex(ciphertext, 24),
        'stored-data entropy': `${s.entropy} bits/byte`,
        'repeated 16-byte blocks': `${s.repeatedBlocksPct}%`,
        'shared with (access list only)': recipients.length ? `${recipients.length} user(s)` : 'nobody',
      },
    });
    for (const st of steps) emit({ ...st, user: req.user.username, route: 'POST /api/files/base' });
    res.json({ file: view(f), steps });
  }),
);

// ------------------------------------------------------------------------------------ BASE download
r.get(
  '/:id/base-download',
  ah(async (req, res) => {
    if (!isId(req.params.id)) return res.status(404).json({ error: 'not found' });
    const f = await File.findById(req.params.id);
    if (!f || f.scheme !== 'base') return res.status(404).json({ error: 'not found' });
    if (!canRead(f, req.user)) {
      emit({ user: req.user.username, title: `Access denied by server ACL for "${f.name}"`, route: 'GET base-download' });
      return res.status(403).json({ error: 'not shared with you (server-side access list)' });
    }
    const owner = await User.findById(f.owner);
    const ct = await getBlob(f.gridId);
    const steps = [
      {
        actor: 'server',
        title: 'CSP loads the ciphertext from GridFS',
        values: { 'stored bytes': hex(ct, 24), 'tampered by attack lab?': f.tampered || 'no' },
      },
    ];
    const out = baseDecryptTraced(ct, fromB64(owner.basePub));
    steps.push(...out.steps);
    steps.push({
      actor: 'server',
      title: out.plain ? 'CSP sends the PLAINTEXT back to the user' : 'CSP could not decrypt (padding error)',
      values: out.plain ? { 'plaintext as text': ascii(out.plain, 60) } : {},
    });
    for (const st of steps) emit({ ...st, user: req.user.username, route: 'GET /api/files/:id/base-download' });
    res.json({
      name: f.name,
      mime: f.mime,
      dataB64: out.plain ? Buffer.from(out.plain).toString('base64') : null,
      error: out.error || null,
      tampered: f.tampered,
      steps,
    });
  }),
);

r.put(
  '/:id/base-share',
  ah(async (req, res) => {
    const f = await File.findById(req.params.id);
    if (!f || f.scheme !== 'base' || String(f.owner) !== String(req.user._id)) return res.status(404).json({ error: 'not found' });
    f.sharedWith = (req.body.userIds || []).filter(isId);
    await f.save();
    emit({
      user: req.user.username,
      route: 'PUT base-share',
      title: `[BASE] access list of "${f.name}" changed - no cryptographic change at all`,
      values: { 'shared with': `${f.sharedWith.length} user(s)`, 'key changed?': 'NO - key is still derived from the public key' },
    });
    res.json(view(f));
  }),
);

// ------------------------------------------------------------------------------------ PROPOSED upload
// Browser already encrypted + signed; server only stores opaque bytes.
r.post(
  '/proposed',
  upload.single('blob'),
  ah(async (req, res) => {
    const ct = new Uint8Array(req.file.buffer);
    const manifest = JSON.parse(req.body.manifest);
    const signature = req.body.signature;
    if (manifest.ownerId !== String(req.user._id)) return res.status(400).json({ error: 'manifest owner mismatch' });
    if (await File.findOne({ fileId: manifest.fileId })) return res.status(409).json({ error: 'fileId exists' });
    const recipients = manifest.recipients.map((x) => x.userId).filter((x) => isId(x) && x !== String(req.user._id));
    const gridId = await putBlob(ct, 'ahe-' + manifest.fileId, { scheme: 'proposed' });
    const f = await File.create({
      scheme: 'proposed',
      owner: req.user._id,
      ownerName: req.user.username,
      size: manifest.size,
      storedSize: ct.length,
      gridId,
      sharedWith: recipients,
      fileId: manifest.fileId,
      manifest,
      signature,
      version: manifest.version,
    });
    const s = stats(ct);
    const steps = [
      {
        actor: 'server',
        title: 'Cloud received ONLY ciphertext + signed manifest (end-to-end encrypted)',
        values: {
          'file name visible to cloud?': 'NO (encrypted inside manifest.encMeta)',
          'received bytes': hex(ct, 24),
          'received-data entropy': `${s.entropy} bits/byte (8.0 = perfectly random)`,
          'repeated 16-byte blocks': `${s.repeatedBlocksPct}%`,
          'locked keys (one per recipient)': String(manifest.recipients.length),
          'can the server decrypt?': 'NO - it holds no DEK and no private key',
        },
      },
      { actor: 'server', title: 'Stored in MongoDB GridFS + manifest in "files" collection', values: { 'GridFS id': String(gridId) } },
    ];
    for (const st of steps) emit({ ...st, user: req.user.username, route: 'POST /api/files/proposed' });
    res.json({ file: view(f), steps });
  }),
);

r.get(
  '/:id/blob',
  ah(async (req, res) => {
    if (!isId(req.params.id)) return res.status(404).json({ error: 'not found' });
    const f = await File.findById(req.params.id);
    if (!f) return res.status(404).json({ error: 'not found' });
    const ct = await getBlob(f.gridId);
    if (!canRead(f, req.user) && wasRecipient(f, req.user))
      emit({
        user: req.user.username,
        route: 'GET /api/files/:id/blob',
        title: `Server deliberately hands the NEW ciphertext to revoked user "${req.user.username}" - only cryptography can stop him now`,
      });
    emit({
      user: req.user.username,
      route: 'GET /api/files/:id/blob',
      title: `Cloud sends ciphertext (${ct.length} B) - decryption happens in the browser`,
      values: { 'sent bytes': hex(ct, 24), 'tampered by attack lab?': f.tampered || 'no' },
    });
    res.set('Content-Type', 'application/octet-stream').send(Buffer.from(ct));
  }),
);

// share = new signed manifest with one more locked key (ciphertext unchanged)
r.put(
  '/:id/proposed-manifest',
  ah(async (req, res) => {
    const f = await File.findById(req.params.id);
    if (!f || f.scheme !== 'proposed' || String(f.owner) !== String(req.user._id)) return res.status(404).json({ error: 'not found' });
    const { manifest, signature } = req.body;
    if (manifest.fileId !== f.fileId || manifest.version !== f.version) return res.status(400).json({ error: 'manifest mismatch' });
    f.manifest = manifest;
    f.signature = signature;
    f.sharedWith = manifest.recipients.map((x) => x.userId).filter((x) => isId(x) && x !== String(req.user._id));
    f.markModified('manifest');
    await f.save();
    emit({
      user: req.user.username,
      route: 'PUT proposed-manifest',
      title: 'Share: stored new signed manifest (ciphertext NOT re-uploaded)',
      values: { 'locked keys now': String(manifest.recipients.length), signature: signature.slice(0, 40) + '…' },
    });
    res.json(view(f));
  }),
);

// revoke = re-key: new ciphertext (new DEK), version + 1
r.put(
  '/:id/proposed-rekey',
  upload.single('blob'),
  ah(async (req, res) => {
    const f = await File.findById(req.params.id);
    if (!f || f.scheme !== 'proposed' || String(f.owner) !== String(req.user._id)) return res.status(404).json({ error: 'not found' });
    const manifest = JSON.parse(req.body.manifest);
    if (manifest.fileId !== f.fileId || manifest.version !== f.version + 1) return res.status(400).json({ error: 'version must increase by 1' });
    const ct = new Uint8Array(req.file.buffer);
    const old = f.gridId;
    f.gridId = await putBlob(ct, 'ahe-' + manifest.fileId + '-v' + manifest.version, { scheme: 'proposed' });
    await deleteBlob(old);
    if (f.backupGridId) await deleteBlob(f.backupGridId);
    f.backupGridId = null;
    f.tampered = null;
    f.manifest = manifest;
    f.signature = req.body.signature;
    f.version = manifest.version;
    f.storedSize = ct.length;
    const newShared = manifest.recipients.map((x) => x.userId).filter((x) => isId(x) && x !== String(req.user._id));
    const removed = f.sharedWith.map(String).filter((x) => !newShared.includes(x));
    f.revoked = [...new Set([...(f.revoked || []).map(String), ...removed])].filter((x) => !newShared.includes(x));
    f.sharedWith = newShared;
    f.markModified('manifest');
    await f.save();
    emit({
      user: req.user.username,
      route: 'PUT proposed-rekey',
      title: `Revocation: version ${manifest.version} stored, old ciphertext deleted`,
      values: { 'new ciphertext': hex(ct, 24), 'locked keys now': String(manifest.recipients.length) },
    });
    res.json(view(f));
  }),
);

r.delete(
  '/:id',
  ah(async (req, res) => {
    const f = await File.findById(req.params.id);
    if (!f || String(f.owner) !== String(req.user._id)) return res.status(404).json({ error: 'not found' });
    await deleteBlob(f.gridId);
    if (f.backupGridId) await deleteBlob(f.backupGridId);
    await f.deleteOne();
    emit({ user: req.user.username, route: 'DELETE /api/files/:id', title: 'File deleted from GridFS' });
    res.json({ ok: true });
  }),
);

export default r;
