import { useEffect, useRef, useState } from 'react';
import { useSession } from '../lib/session.jsx';
import { useTrace } from '../lib/trace.jsx';
import { getJSON, api } from '../lib/api.js';
import { openFile, bytesToPreview } from '../lib/fileops.js';
import { useFiles, PreviewModal } from './Dashboard.jsx';
import { encryptFile } from '@cryptovault/crypto-core/proposed';
import { shannonEntropy, repeatedBlockRatio } from '@cryptovault/crypto-core/analysis';
import { SchemeBadge } from '../components/Badge.jsx';

function FilePick({ files, names, scheme, value, onChange }) {
  const list = files.filter((f) => f.scheme === scheme);
  return (
    <select value={value || ''} onChange={(e) => onChange(e.target.value)}>
      <option value="">- choose a {scheme === 'base' ? 'BASE' : 'PROPOSED'} file -</option>
      {list.map((f) => (
        <option key={f.id} value={f.id}>
          {names[f.id] || f.id} · owner {f.ownerName} · v{f.version}
        </option>
      ))}
    </select>
  );
}

function Result({ r }) {
  if (!r) return <div className="result empty">not run yet</div>;
  return (
    <div className={`result ${r.bad ? 'bad' : 'good'}`}>
      <b>{r.head}</b>
      {r.body && <pre>{r.body}</pre>}
      {r.img && <img src={r.img} alt="" />}
    </div>
  );
}

export default function AttackLab() {
  const session = useSession();
  const trace = useTrace();
  const { files, names, load } = useFiles();
  const [sel, setSel] = useState({ base: '', proposed: '' });
  const [a1, setA1] = useState({});
  const [a2, setA2] = useState({});
  const [kind, setKind] = useState('block_swap');
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    // pre-select the newest file of each scheme
    const b = files.find((f) => f.scheme === 'base');
    const p = files.find((f) => f.scheme === 'proposed');
    setSel((s) => ({ base: s.base || b?.id || '', proposed: s.proposed || p?.id || '' }));
  }, [files]);

  const wrap = async (fn) => {
    setBusy(true);
    try {
      await fn();
    } catch (e) {
      alert(e.message);
    } finally {
      setBusy(false);
    }
  };

  // ---------------- attack 1
  const runA1 = (scheme) =>
    wrap(async () => {
      const id = sel[scheme];
      if (!id) return;
      trace.operation(`ATTACK 1 on ${scheme.toUpperCase()} file: decrypt using only public information`, 'op');
      const r = await getJSON(`/lab/public-key-attack/${id}`, { method: 'POST' });
      trace.pushMany(r.steps);
      let img = null;
      if (r.preview?.b64) img = `data:${r.preview.mime};base64,${r.preview.b64}`;
      setA1((s) => ({
        ...s,
        [scheme]: r.success
          ? { bad: true, head: 'Attacker recovered the whole file', body: img ? null : r.preview?.text, img }
          : { bad: false, head: 'Attack failed: no key can be derived from public data', body: r.steps[r.steps.length - 1].title },
      }));
    });

  // ---------------- attack 2
  const runA2 = (scheme) =>
    wrap(async () => {
      const id = sel[scheme];
      if (!id) return;
      trace.operation(`ATTACK 2 on ${scheme.toUpperCase()} file: malicious cloud edits stored bytes (${kind})`, 'op');
      const r = await getJSON(`/lab/tamper/${id}`, { method: 'POST', body: { kind } });
      trace.pushMany(r.steps);
      await load();
      setA2((s) => ({ ...s, [scheme]: { bad: false, head: 'Ciphertext modified in the cloud. Now click "Open as me".' } }));
    });
  const openA2 = (scheme) =>
    wrap(async () => {
      const fs = await getJSON('/files');
      const f = fs.find((x) => x.id === sel[scheme]);
      const r = await openFile(f, session, trace);
      if (r.ok) {
        const v = bytesToPreview(r.bytes, r.mime);
        setA2((s) => ({
          ...s,
          [scheme]: {
            bad: !!f.tampered,
            head: f.tampered ? 'Decrypted WITHOUT any warning, but the content was changed:' : 'Opened normally (file is untouched):',
            body: v.kind === 'text' ? v.text : null,
            img: v.kind === 'image' ? v.url : null,
          },
        }));
      } else setA2((s) => ({ ...s, [scheme]: { bad: false, head: 'BLOCKED: tampering detected, no data released', body: r.error } }));
    });
  const restore = () =>
    wrap(async () => {
      for (const id of [sel.base, sel.proposed]) if (id) await api(`/lab/restore/${id}`, { method: 'POST' });
      trace.push({ actor: 'server', title: 'Attack Lab: original ciphertexts restored' });
      setA2({});
      load();
    });

  return (
    <div>
      <h2>Attack Lab</h2>
      <p className="muted">
        Each attack runs for real against the stored data. The server plays the attacker, and every step it takes appears in the Crypto Inspector. Choose one file of each scheme (upload the same sample with both schemes first):
      </p>
      <div className="card row wrap">
        <div>
          <SchemeBadge scheme="base" />
          <FilePick files={files} names={names} scheme="base" value={sel.base} onChange={(v) => setSel({ ...sel, base: v })} />
        </div>
        <div>
          <SchemeBadge scheme="proposed" />
          <FilePick files={files} names={names} scheme="proposed" value={sel.proposed} onChange={(v) => setSel({ ...sel, proposed: v })} />
        </div>
      </div>

      <div className="card attack">
        <h3>
          <span className="anum">1</span> Decrypt with only PUBLIC information <small>(weakness W1: the key is computed from the public key)</small>
        </h3>
        <p className="muted">
          The attacker has a leaked copy of the stored ciphertext and reads the owner's public key from the directory, which anyone can do. No password, no private key, no brute force.
        </p>
        <div className="vs">
          <div>
            <button className="btn danger" disabled={busy || !sel.base} onClick={() => runA1('base')}>
              Attack the BASE file
            </button>
            <Result r={a1.base} />
          </div>
          <div>
            <button className="btn danger" disabled={busy || !sel.proposed} onClick={() => runA1('proposed')}>
              Attack the PROPOSED file
            </button>
            <Result r={a1.proposed} />
          </div>
        </div>
      </div>

      <div className="card attack">
        <h3>
          <span className="anum">2</span> Cloud insider modifies the stored file <small>(weakness W2: no integrity check)</small>
        </h3>
        <p className="muted">
          Tip: use <b>payment_order.txt</b> and "swap blocks 2 ↔ 4". In ECB, every 16-byte block is encrypted separately, so swapping two ciphertext blocks swaps the two amounts after decryption.
        </p>
        <div className="row wrap">
          <select value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="block_swap">Swap ciphertext blocks 2 ↔ 4</option>
            <option value="bit_flip">Flip a single bit</option>
            <option value="delete_block">Delete one 16-byte block</option>
          </select>
          <button className="btn ghost sm" onClick={restore} disabled={busy}>
            Restore originals
          </button>
        </div>
        <div className="vs">
          <div>
            <div className="row">
              <button className="btn danger" disabled={busy || !sel.base} onClick={() => runA2('base')}>
                Tamper BASE file
              </button>
              <button className="btn" disabled={busy || !sel.base} onClick={() => openA2('base')}>
                Open as me
              </button>
            </div>
            <Result r={a2.base} />
          </div>
          <div>
            <div className="row">
              <button className="btn danger" disabled={busy || !sel.proposed} onClick={() => runA2('proposed')}>
                Tamper PROPOSED file
              </button>
              <button className="btn" disabled={busy || !sel.proposed} onClick={() => openA2('proposed')}>
                Open as me
              </button>
            </div>
            <Result r={a2.proposed} />
          </div>
        </div>
      </div>

      <EcbCard session={session} trace={trace} />

      <div className="card attack">
        <h3>
          <span className="anum">4</span> Revoked user <small>(weakness W3: no real sharing / revocation)</small>
        </h3>
        <ol className="steps">
          <li>
            As <b>alice</b>, share one BASE file and one PROPOSED file with <b>bob</b> (Files → Share / Revoke).
          </li>
          <li>
            Revoke bob from both files. <b>BASE</b> only edits a server access list. <b>PROPOSED</b> re-encrypts under a new random key (version 2) and locks it only for the remaining users. Watch the Inspector.
          </li>
          <li>
            In bob's window: the PROPOSED file shows "🔒 no key for this version" and opening it is denied. For the BASE file, bob (or anyone) still knows alice's public key, so Attack 1 decrypts any copy he obtains. Revocation means nothing there.
          </li>
        </ol>
      </div>
      {preview && <PreviewModal p={preview} onClose={() => setPreview(null)} />}
    </div>
  );
}

// ------------------------------------------------------------------- attack 3: ECB image leak
function EcbCard({ session, trace }) {
  const c0 = useRef(null);
  const c1 = useRef(null);
  const c2 = useRef(null);
  const [st, setSt] = useState(null);
  const [busy, setBusy] = useState(false);

  const draw = (canvas, w, h, bytes) => {
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext('2d');
    const img = ctx.createImageData(w, h);
    img.data.set(bytes.subarray(0, w * h * 4));
    for (let i = 3; i < img.data.length; i += 4) img.data[i] = 255; // force opaque
    ctx.putImageData(img, 0, 0);
  };

  const run = async (src) => {
    setBusy(true);
    try {
      const im = new Image();
      im.src = src;
      await im.decode();
      const w = im.width - (im.width % 4);
      const h = im.height;
      const cv = document.createElement('canvas');
      cv.width = w;
      cv.height = h;
      const cx = cv.getContext('2d');
      cx.drawImage(im, 0, 0);
      const px = new Uint8Array(cx.getImageData(0, 0, w, h).data.buffer);
      draw(c0.current, w, h, px);
      trace.operation('ATTACK 3: pattern leakage. Encrypt the same image with both schemes and draw the ciphertext as pixels', 'op');
      trace.push({
        actor: 'browser',
        title: 'Read raw RGBA pixels from the image',
        values: { size: `${w}×${h}`, bytes: String(px.length), 'repeated 16-byte blocks in plaintext': `${(100 * repeatedBlockRatio(px)).toFixed(1)}%` },
      });
      const res = await api('/lab/ecb', { method: 'POST', raw: px });
      const ecb = new Uint8Array(await res.arrayBuffer());
      draw(c1.current, w, h, ecb);
      const { ciphertext } = await encryptFile(
        px,
        { fileId: crypto.randomUUID(), ownerId: session.user.id, name: 'img', mime: 'image/raw' },
        [{ userId: session.user.id, ...session.pubOf(session.user.id) }],
        session.keys.ecdsaPriv,
        undefined,
        trace.tracer,
      );
      const gcm = ciphertext.subarray(0, px.length);
      draw(c2.current, w, h, gcm);
      const s = (b) => ({ e: shannonEntropy(b), r: 100 * repeatedBlockRatio(b) });
      setSt({ p: s(px), b: s(ecb), g: s(gcm) });
    } catch (e) {
      alert(e.message);
    } finally {
      setBusy(false);
    }
  };

  const onFile = (e) => {
    const f = e.target.files[0];
    if (f) run(URL.createObjectURL(f));
  };

  const S = ({ s }) => (s ? <small className="muted">entropy {s.e.toFixed(3)} bits/byte · repeated blocks {s.r.toFixed(1)}%</small> : null);

  return (
    <div className="card attack">
      <h3>
        <span className="anum">3</span> Pattern leakage <small>(ECB: equal plaintext blocks give equal ciphertext blocks)</small>
      </h3>
      <div className="row wrap">
        <button className="btn danger" disabled={busy} onClick={() => run('/samples/cloud_logo.png')}>
          Run with sample logo
        </button>
        <label className="chip file">
          or choose an image…
          <input type="file" accept="image/*" hidden onChange={onFile} />
        </label>
      </div>
      <div className="ecb-grid">
        <figure>
          <canvas ref={c0} />
          <figcaption>
            Original <S s={st?.p} />
          </figcaption>
        </figure>
        <figure>
          <canvas ref={c1} />
          <figcaption>
            <b className="red-t">BASE: AES-ECB ciphertext</b> <S s={st?.b} />
          </figcaption>
        </figure>
        <figure>
          <canvas ref={c2} />
          <figcaption>
            <b className="green-t">PROPOSED: AES-256-GCM ciphertext</b> <S s={st?.g} />
          </figcaption>
        </figure>
      </div>
    </div>
  );
}
