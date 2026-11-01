import { useEffect, useState, useRef } from 'react';
import { getJSON, getToken } from '../lib/api.js';
import { SchemeBadge, EntropyBar } from '../components/Badge.jsx';

export default function CloudView() {
  const [rows, setRows] = useState([]);
  const [log, setLog] = useState([]);
  const timer = useRef(null);
  const load = async () => setRows(await getJSON('/lab/dump'));
  useEffect(() => {
    load();
    getJSON('/events/recent').then((r) => setLog((l) => [...l, ...r.reverse()]));
    const es = new EventSource('/api/events?token=' + encodeURIComponent(getToken() || ''));
    es.onmessage = (m) => {
      const e = JSON.parse(m.data);
      setLog((l) => [e, ...l].slice(0, 120));
      clearTimeout(timer.current);
      timer.current = setTimeout(load, 400);
    };
    return () => es.close();
  }, []);
  return (
    <div>
      <h2>What the cloud actually stores</h2>
      <p className="muted">
        This is a raw view of the MongoDB/GridFS contents, i.e. what a cloud admin, a hacker with a leaked backup, or a malicious insider would see. It updates live. (Byte entropy is
        only meaningful for files of a few KB or more: a 112-byte file cannot reach 8 bits/byte, because it has fewer than 256 bytes.)
      </p>
      <div className="card">
        <table className="tbl mono-sm">
          <thead>
            <tr>
              <th>Scheme</th>
              <th>Owner</th>
              <th>File name stored</th>
              <th>Stored bytes (first 48)</th>
              <th>Entropy (bits/byte)</th>
              <th>Repeated blocks</th>
              <th>Keys</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>
                  <SchemeBadge scheme={r.scheme} />
                  {r.tampered && <span className="badge amber">tampered</span>}
                </td>
                <td>{r.ownerName}</td>
                <td>{r.storedName}</td>
                <td>
                  <code className="hexcell">{r.first48}</code>
                </td>
                <td style={{ minWidth: 140 }}>
                  <EntropyBar value={r.entropy} />
                </td>
                <td>{r.repeatedBlocksPct}%</td>
                <td>{r.scheme === 'base' ? 'derivable from public key' : `${r.recipients} locked (ECDH)`}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="card">
        <h3>Live cloud-server log (Server-Sent Events, all users)</h3>
        <div className="srvlog">
          {log.map((e, i) => (
            <div key={i} className={`srvline a-${e.actor}`}>
              <span className="t">{new Date(e.at).toLocaleTimeString()}</span>
              <span className="who">{e.actor === 'attacker' ? 'ATTACKER' : e.user || ''}</span>
              <span>{e.title}</span>
              {e.values && (
                <div className="kv">
                  {Object.entries(e.values).map(([k, v]) => (
                    <span key={k}>
                      {k}: <code>{String(v)}</code>
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
