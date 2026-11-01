import { useEffect, useRef } from 'react';
import { useTrace } from '../lib/trace.jsx';

const ACTOR = {
  browser: { label: 'BROWSER', cls: 'a-browser' },
  client: { label: 'BROWSER', cls: 'a-browser' },
  server: { label: 'CLOUD SERVER', cls: 'a-server' },
  attacker: { label: 'ATTACKER', cls: 'a-attacker' },
  op: { label: 'OPERATION', cls: 'a-op' },
  system: { label: 'SYSTEM', cls: 'a-op' },
};

function Flow({ active }) {
  const node = (k, label, sub) => (
    <div className={`flow-node ${active === k ? 'on' : ''} n-${k}`}>
      <b>{label}</b>
      <small>{sub}</small>
    </div>
  );
  return (
    <div className="flow">
      {node('browser', 'Browser', 'keys live here')}
      <div className={`flow-wire ${active === 'browser' || active === 'server' ? 'pulse' : ''}`} />
      {node('server', 'Cloud', 'Express + MongoDB')}
      <div className={`flow-wire ${active === 'attacker' ? 'pulse red' : ''}`} />
      {node('attacker', 'Attacker', 'insider / leak')}
    </div>
  );
}

export default function Inspector() {
  const { shown, queue, mode, setMode, next, flush, clear } = useTrace();
  const end = useRef(null);
  useEffect(() => {
    end.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [shown.length]);
  const last = shown[shown.length - 1];
  const active = last ? (last.actor === 'client' ? 'browser' : last.actor) : null;
  let n = 0;
  return (
    <aside className="inspector">
      <div className="insp-head">
        <div>
          <h3>Crypto Inspector</h3>
          <small>every real step, with the real bytes</small>
        </div>
        <div className="insp-ctl">
          <select value={mode} onChange={(e) => setMode(e.target.value)} title="Live: show immediately. Step: reveal one step per click.">
            <option value="live">Live</option>
            <option value="step">Step-by-step</option>
            <option value="auto">Auto-play</option>
          </select>
          {mode !== 'live' && (
            <>
              <button className="btn sm primary" onClick={next} disabled={!queue.length}>
                Next ▶ {queue.length ? `(${queue.length})` : ''}
              </button>
              <button className="btn sm" onClick={flush} disabled={!queue.length}>
                All
              </button>
            </>
          )}
          <button className="btn sm ghost" onClick={clear}>
            Clear
          </button>
        </div>
      </div>
      <Flow active={active} />
      <div className="insp-list">
        {!shown.length && <p className="muted pad">Log in, upload or open a file, or run an attack. Each cryptographic step appears here.</p>}
        {shown.map((e) => {
          const a = ACTOR[e.actor] || ACTOR.system;
          if (e.actor === 'op')
            return (
              <div key={e.id} className="ev-op">
                <span>▸</span> {e.title}
              </div>
            );
          n++;
          return (
            <div key={e.id} className={`ev ${a.cls}`}>
              <div className="ev-top">
                <span className="ev-n">{n}</span>
                <span className="ev-actor">{a.label}</span>
                {e.ms != null && <span className="ev-ms">{e.ms} ms</span>}
              </div>
              <div className="ev-title">{e.title}</div>
              {e.values && Object.keys(e.values).length > 0 && (
                <table className="ev-vals">
                  <tbody>
                    {Object.entries(e.values).map(([k, v]) => (
                      <tr key={k}>
                        <td>{k}</td>
                        <td>
                          <code>{String(v)}</code>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          );
        })}
        <div ref={end} />
      </div>
    </aside>
  );
}
