import { useEffect, useState, useCallback } from 'react';
import { useSession } from '../lib/session.jsx';
import { useTrace } from '../lib/trace.jsx';
import { getJSON, api } from '../lib/api.js';
import { uploadBase, uploadProposed, openFile, shareFile, revokeUser, bytesToPreview, download } from '../lib/fileops.js';
import { decryptMeta } from '@cryptovault/crypto-core/proposed';
import Modal from '../components/Modal.jsx';
import { SchemeBadge } from '../components/Badge.jsx';

const SAMPLES = [
  ['payment_order.txt', 'text/plain'],
  ['salary_records.csv', 'text/csv'],
  ['cloud_logo.png', 'image/png'],
];

export function useFiles() {
  const session = useSession();
  const [files, setFiles] = useState([]);
  const [names, setNames] = useState({});
  const load = useCallback(async () => {
    const fs = await getJSON('/files');
    setFiles(fs);
    const nm = {};
    for (const f of fs) {
      if (f.scheme === 'base') nm[f.id] = f.name;
      else {
        try {
          const m = await decryptMeta(f.manifest, session.me);
          nm[f.id] = m ? m.name : '🔒 (no key for this version)';
        } catch {
          nm[f.id] = '🔒 (cannot unlock)';
        }
      }
    }
    setNames(nm);
  }, [session.me]);
  useEffect(() => {
    load();
  }, [load]);
  return { files, names, load };
}

export default function Dashboard() {
  const session = useSession();
  const trace = useTrace();
  const { user, directory } = session;
  const { files, names, load } = useFiles();
  const [scheme, setScheme] = useState('proposed');
  const [picked, setPicked] = useState(null); // {name,type,bytes}
  const [rcpts, setRcpts] = useState([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  const [preview, setPreview] = useState(null);
  const [shareFor, setShareFor] = useState(null);

  const others = directory.filter((u) => u.id !== user.id);

  const pickSample = async (name, type) => {
    const b = new Uint8Array(await (await fetch('/samples/' + name)).arrayBuffer());
    setPicked({ name, type, bytes: b });
  };
  const pickFile = async (ev) => {
    const f = ev.target.files[0];
    if (!f) return;
    setPicked({ name: f.name, type: f.type, bytes: new Uint8Array(await f.arrayBuffer()) });
  };

  const doUpload = async () => {
    if (!picked) return;
    setBusy(true);
    setMsg(null);
    try {
      const file = { name: picked.name, type: picked.type };
      if (scheme === 'base') await uploadBase(file, picked.bytes, rcpts, trace);
      else await uploadProposed(file, picked.bytes, rcpts, session, trace);
      setMsg({ c: 'green', t: `Uploaded "${picked.name}" with the ${scheme === 'base' ? 'BASE' : 'PROPOSED'} scheme.` });
      await load();
    } catch (e) {
      setMsg({ c: 'red', t: e.message });
    } finally {
      setBusy(false);
    }
  };

  const doOpen = async (f) => {
    setBusy(true);
    try {
      const r = await openFile(f, session, trace);
      setPreview({ f, ...r, view: r.ok ? bytesToPreview(r.bytes, r.mime) : null });
    } catch (e) {
      setPreview({ f, ok: false, error: e.message });
    } finally {
      setBusy(false);
    }
  };

  const doDelete = async (f) => {
    if (!confirm('Delete this file?')) return;
    await api(`/files/${f.id}`, { method: 'DELETE' });
    load();
  };

  return (
    <div>
      <h2>My cloud files</h2>
      <p className="muted">
        Upload the same file once with each scheme, then open it, share it, or attack it in the <b>Attack Lab</b>. Watch the <b>Crypto Inspector</b> →
      </p>

      <div className="card">
        <h3>1 · Choose a file</h3>
        <div className="row wrap">
          {SAMPLES.map(([n, t]) => (
            <button key={n} className={`chip ${picked?.name === n ? 'on' : ''}`} onClick={() => pickSample(n, t)}>
              {n}
            </button>
          ))}
          <label className="chip file">
            Your own file…
            <input type="file" onChange={pickFile} hidden />
          </label>
          {picked && (
            <span className="muted">
              selected: <b>{picked.name}</b> ({picked.bytes.length} B)
            </span>
          )}
        </div>
        <h3>2 · Choose the scheme</h3>
        <div className="scheme-pick">
          <button className={`scheme base ${scheme === 'base' ? 'on' : ''}`} onClick={() => setScheme('base')}>
            <b>Base paper · AES-ECC</b>
            <small>Rehman et al., Electronics 2021. The cloud server encrypts with an AES key derived from your ECC public key.</small>
          </button>
          <button className={`scheme prop ${scheme === 'proposed' ? 'on' : ''}`} onClick={() => setScheme('proposed')}>
            <b>Proposed · AES-GCM + ECDH + ECDSA</b>
            <small>Your browser encrypts with a random key, locks it for each recipient and signs the upload. The cloud sees only ciphertext.</small>
          </button>
        </div>
        <h3>3 · Share with (optional)</h3>
        <div className="row wrap">
          {others.map((u) => (
            <label key={u.id} className={`chip ${rcpts.includes(u.id) ? 'on' : ''}`}>
              <input
                type="checkbox"
                hidden
                checked={rcpts.includes(u.id)}
                onChange={(e) => setRcpts(e.target.checked ? [...rcpts, u.id] : rcpts.filter((x) => x !== u.id))}
              />
              {u.username}
            </label>
          ))}
        </div>
        <div className="row" style={{ marginTop: 14 }}>
          <button className="btn primary" disabled={!picked || busy} onClick={doUpload}>
            {busy ? 'Working…' : 'Encrypt & upload'}
          </button>
          {msg && <span className={`alert inline ${msg.c}`}>{msg.t}</span>}
        </div>
      </div>

      <div className="card">
        <div className="row between">
          <h3>Files I own or that are shared with me</h3>
          <button className="btn sm ghost" onClick={load}>
            Refresh
          </button>
        </div>
        <table className="tbl">
          <thead>
            <tr>
              <th>Name</th>
              <th>Scheme</th>
              <th>Owner</th>
              <th>Size</th>
              <th>Ver</th>
              <th>Shared</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {files.map((f) => (
              <tr key={f.id}>
                <td>
                  {names[f.id] || '…'} {f.tampered && <span className="badge amber">cloud-tampered</span>}
                  {f.revoked?.includes(user.id) && <span className="badge red">access revoked</span>}
                </td>
                <td>
                  <SchemeBadge scheme={f.scheme} />
                </td>
                <td>{f.ownerName}</td>
                <td>{f.size} B</td>
                <td>v{f.version}</td>
                <td>{f.sharedWith.length}</td>
                <td className="actions">
                  <button className="btn sm primary" onClick={() => doOpen(f)} disabled={busy}>
                    Open
                  </button>
                  {f.owner === user.id && (
                    <>
                      <button className="btn sm" onClick={() => setShareFor(f)}>
                        Share / Revoke
                      </button>
                      <button className="btn sm ghost" onClick={() => doDelete(f)}>
                        ✕
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
            {!files.length && (
              <tr>
                <td colSpan={7} className="muted">
                  No files yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {preview && <PreviewModal p={preview} onClose={() => setPreview(null)} />}
      {shareFor && (
        <ShareModal
          f={shareFor}
          others={others}
          onClose={() => setShareFor(null)}
          onDone={() => {
            setShareFor(null);
            load();
          }}
        />
      )}
    </div>
  );
}

export function PreviewModal({ p, onClose }) {
  return (
    <Modal title={p.ok ? `Opened: ${p.name}` : 'Could not open file'} onClose={onClose} wide>
      {!p.ok && (
        <div className={`alert big ${p.stage === 'access' ? 'amber' : 'red'}`}>
          <b>{p.stage === 'access' ? 'ACCESS DENIED' : 'BLOCKED: TAMPERING DETECTED'}</b>
          <div>{p.error}</div>
          <small>No plaintext was released. The Crypto Inspector shows which check failed.</small>
        </div>
      )}
      {p.ok && p.tampered && (
        <div className="alert big amber">
          <b>The cloud modified this file ({p.tampered}), and the BASE scheme gave no warning.</b>
          <div>The content below decrypted "successfully". Compare the amounts with the original payment order.</div>
        </div>
      )}
      {p.ok && p.view?.kind === 'text' && <pre className="preview">{p.view.text}</pre>}
      {p.ok && p.view?.kind === 'image' && <img className="preview-img" src={p.view.url} alt="" />}
      {p.ok && (
        <button className="btn sm" onClick={() => download(p.bytes, p.name, p.mime)}>
          Save file
        </button>
      )}
    </Modal>
  );
}

function ShareModal({ f, others, onClose, onDone }) {
  const session = useSession();
  const trace = useTrace();
  const current = f.scheme === 'base' ? f.sharedWith : f.manifest.recipients.map((r) => r.userId).filter((x) => x !== f.owner);
  const [sel, setSel] = useState(current);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const run = async (fn) => {
    setBusy(true);
    setErr('');
    try {
      await fn();
      onDone();
    } catch (e) {
      setErr(e.message);
      setBusy(false);
    }
  };
  return (
    <Modal title="Share / revoke access" onClose={onClose}>
      <p className="muted">
        {f.scheme === 'base'
          ? 'BASE: sharing only edits the server access list. The encryption key does not change.'
          : 'PROPOSED: sharing adds a locked copy of the file key (ECDH). Revoking re-encrypts under a NEW key (new version).'}
      </p>
      {others.map((u) => {
        const has = current.includes(u.id);
        return (
          <div key={u.id} className="row between share-row">
            <label>
              <input type="checkbox" checked={sel.includes(u.id)} disabled={has} onChange={(e) => setSel(e.target.checked ? [...sel, u.id] : sel.filter((x) => x !== u.id))} />{' '}
              {u.username} <small className="muted">🔑 {u.fingerprint.slice(0, 14)}</small>
            </label>
            {has && (
              <button className="btn sm danger" disabled={busy} onClick={() => run(() => revokeUser(f, u.id, session, trace))}>
                Revoke
              </button>
            )}
          </div>
        );
      })}
      {err && <div className="alert red">{err}</div>}
      <button className="btn primary" disabled={busy} onClick={() => run(() => shareFile(f, sel, session, trace))}>
        Share with selected
      </button>
    </Modal>
  );
}
