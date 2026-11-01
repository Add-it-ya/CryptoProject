// High-level file operations used by the Dashboard and the Attack Lab. Each one narrates what happens
// (browser side through `trace`, server side through the `steps` the API returns).
import { api, getJSON, getBytes } from './api.js';
import { encryptFile, decryptFile, addRecipient, rekeyFile, hx, IntegrityError, AccessError } from '@cryptovault/crypto-core/proposed';
import { fromB64, td } from '@cryptovault/crypto-core/encoding';
import { shannonEntropy } from '@cryptovault/crypto-core/analysis';

const ascii = (b, n = 60) =>
  Array.from(b.subarray(0, n))
    .map((c) => (c >= 32 && c < 127 ? String.fromCharCode(c) : '·'))
    .join('');

export async function uploadBase(file, bytes, recipientIds, trace) {
  trace.operation(`UPLOAD "${file.name}" with BASE scheme (Rehman et al. 2021: AES-ECC)`);
  trace.push({
    actor: 'browser',
    title: 'Browser sends the file AS PLAINTEXT to the cloud service provider (paper Fig. 3: CSP encrypts)',
    values: {
      'request body (what travels / what the CSP sees)': ascii(bytes),
      'file name sent': file.name,
      'Shannon entropy of data': `${shannonEntropy(bytes).toFixed(3)} bits/byte`,
    },
  });
  const form = new FormData();
  form.append('file', new Blob([bytes], { type: file.type || 'application/octet-stream' }), file.name);
  form.append('recipients', JSON.stringify(recipientIds));
  const res = await getJSON('/files/base', { method: 'POST', form });
  trace.pushMany(res.steps);
  return res.file;
}

export async function uploadProposed(file, bytes, recipientIds, session, trace) {
  const { user, keys, pubOf } = session;
  trace.operation(`UPLOAD "${file.name}" with PROPOSED scheme (AES-256-GCM + ECDH + ECDSA)`);
  const fileId = crypto.randomUUID();
  const recipients = [user.id, ...recipientIds].map((id) => ({ userId: id, ...pubOf(id) }));
  const { ciphertext, manifest, signature } = await encryptFile(
    bytes,
    { fileId, ownerId: user.id, version: 1, name: file.name, mime: file.type || 'application/octet-stream' },
    recipients,
    keys.ecdsaPriv,
    undefined,
    trace.tracer,
  );
  trace.push({
    actor: 'browser',
    title: 'Browser uploads ciphertext + signed manifest (this is the ENTIRE request body)',
    values: {
      'ciphertext bytes': hx(ciphertext, 24),
      'Shannon entropy of upload': `${shannonEntropy(ciphertext).toFixed(4)} bits/byte`,
      'manifest.recipients': manifest.recipients.map((r) => pubOf(r.userId)?.label || r.userId).join(', '),
    },
  });
  const form = new FormData();
  form.append('blob', new Blob([ciphertext]), 'blob');
  form.append('manifest', JSON.stringify(manifest));
  form.append('signature', signature);
  const res = await getJSON('/files/proposed', { method: 'POST', form });
  trace.pushMany(res.steps);
  return res.file;
}

/** Download + decrypt. Returns { ok, bytes, name, mime, error, stage } */
export async function openFile(f, session, trace) {
  const { me, pubOf, user } = session;
  if (f.scheme === 'base') {
    trace.operation(`OPEN "${f.name}" (BASE scheme) as ${user.username}`);
    trace.push({ actor: 'browser', title: 'Browser asks the CSP to decrypt the file for us', values: { request: `GET /api/files/${f.id}/base-download` } });
    const res = await getJSON(`/files/${f.id}/base-download`);
    trace.pushMany(res.steps);
    if (!res.dataB64) return { ok: false, error: 'Decryption failed (padding error)', stage: 'padding', name: f.name };
    const bytes = fromB64(res.dataB64);
    trace.push({
      actor: 'browser',
      title: res.tampered ? 'Browser received data - NO WARNING, although the cloud modified it!' : 'Browser received plaintext from the CSP',
      values: { 'received plaintext': ascii(bytes), 'integrity proof received?': 'none (scheme has no tag/signature)' },
    });
    return { ok: true, bytes, name: res.name, mime: res.mime, tampered: res.tampered };
  }
  trace.operation(`OPEN file v${f.version} (PROPOSED scheme) as ${user.username}`);
  const ct = await getBytes(`/files/${f.id}/blob`);
  trace.push({
    actor: 'browser',
    title: 'Downloaded ciphertext + manifest from the cloud; decrypting LOCALLY',
    values: { 'ciphertext bytes': hx(ct, 24), owner: f.ownerName },
  });
  const ownerPub = pubOf(f.owner);
  try {
    const { plain, meta } = await decryptFile(ct, f.manifest, f.signature, me, ownerPub.ecdsaPub, trace.tracer);
    trace.push({ actor: 'browser', title: `File verified + decrypted: "${meta.name}"`, values: { content: ascii(plain) } });
    return { ok: true, bytes: plain, name: meta.name, mime: meta.mime };
  } catch (e) {
    const blocked = e instanceof IntegrityError;
    trace.push({
      actor: 'browser',
      title: blocked ? `BLOCKED - tampering detected (${e.stage})` : `DENIED - ${e.message}`,
      values: { reason: e.message },
    });
    return { ok: false, error: e.message, stage: e.stage || (e instanceof AccessError ? 'access' : 'error') };
  }
}

export async function shareFile(f, userIds, session, trace) {
  if (f.scheme === 'base') {
    trace.operation(`SHARE "${f.name}" (BASE): only the server's access list changes`);
    const res = await getJSON(`/files/${f.id}/base-share`, { method: 'PUT', body: { userIds } });
    trace.push({ actor: 'server', title: 'CSP updated its access list. The encryption key is unchanged and still public-derived.' });
    return res;
  }
  const { me, keys, pubOf } = session;
  let manifest = f.manifest;
  let signature = f.signature;
  const already = new Set(manifest.recipients.map((r) => r.userId));
  for (const id of userIds.filter((x) => !already.has(x))) {
    trace.operation(`SHARE file with ${pubOf(id).label} (PROPOSED): add one locked key, no re-encryption`);
    ({ manifest, signature } = await addRecipient(manifest, me, { userId: id, ...pubOf(id) }, keys.ecdsaPriv, trace.tracer));
  }
  return getJSON(`/files/${f.id}/proposed-manifest`, { method: 'PUT', body: { manifest, signature } });
}

export async function revokeUser(f, userId, session, trace) {
  const { me, keys, pubOf, user } = session;
  if (f.scheme === 'base') {
    trace.operation(`REVOKE ${pubOf(userId)?.label} from "${f.name}" (BASE)`);
    const res = await getJSON(`/files/${f.id}/base-share`, { method: 'PUT', body: { userIds: f.sharedWith.filter((x) => x !== userId) } });
    trace.push({
      actor: 'browser',
      title: 'Removed from the server access list only - the revoked user can still decrypt any copy using the public key (Attack 1)',
    });
    return res;
  }
  trace.operation(`REVOKE ${pubOf(userId)?.label} (PROPOSED): re-key to a new version`);
  const ct = await getBytes(`/files/${f.id}/blob`);
  const remaining = f.manifest.recipients.map((r) => r.userId).filter((id) => id !== userId);
  const res = await rekeyFile(
    ct,
    f.manifest,
    f.signature,
    me,
    pubOf(user.id).ecdsaPub,
    remaining.map((id) => ({ userId: id, ...pubOf(id) })),
    keys.ecdsaPriv,
    trace.tracer,
  );
  const form = new FormData();
  form.append('blob', new Blob([res.ciphertext]), 'blob');
  form.append('manifest', JSON.stringify(res.manifest));
  form.append('signature', res.signature);
  return getJSON(`/files/${f.id}/proposed-rekey`, { method: 'PUT', form });
}

export function bytesToPreview(bytes, mime) {
  if (mime && mime.startsWith('image/')) return { kind: 'image', url: URL.createObjectURL(new Blob([bytes], { type: mime })) };
  return { kind: 'text', text: td.decode(bytes.subarray(0, 20000)) };
}

export function download(bytes, name, mime) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([bytes], { type: mime || 'application/octet-stream' }));
  a.download = name || 'file';
  a.click();
}

export { api };
