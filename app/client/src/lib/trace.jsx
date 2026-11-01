// Crypto Inspector state. Every operation pushes "events" (browser crypto steps, server steps returned
// by the API, attacker steps). In STEP mode the events are queued and revealed one click at a time so
// the presenter can explain each step while the audience sees the real values.
import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';

const Ctx = createContext(null);
let seq = 0;

export function TraceProvider({ children }) {
  const [shown, setShown] = useState([]);
  const [queue, setQueue] = useState([]);
  const [mode, setMode] = useState('live'); // live | step | auto
  const modeRef = useRef(mode);
  modeRef.current = mode;

  const push = useCallback((e) => {
    const ev = { ...e, id: ++seq, at: e.at || Date.now() };
    if (modeRef.current === 'live') setShown((s) => [...s.slice(-250), ev]);
    else setQueue((q) => [...q, ev]);
  }, []);
  const pushMany = useCallback((arr) => (arr || []).forEach((e) => push(e)), [push]);
  const operation = useCallback((title, actor = 'op') => push({ actor, title }), [push]);
  const next = useCallback(() => {
    setQueue((q) => {
      if (!q.length) return q;
      setShown((s) => [...s.slice(-250), q[0]]);
      return q.slice(1);
    });
  }, []);
  const flush = useCallback(() => {
    setQueue((q) => {
      setShown((s) => [...s, ...q].slice(-250));
      return [];
    });
  }, []);
  const clear = useCallback(() => {
    setShown([]);
    setQueue([]);
  }, []);

  useEffect(() => {
    if (mode !== 'auto') return;
    const t = setInterval(next, 1100);
    return () => clearInterval(t);
  }, [mode, next]);
  useEffect(() => {
    if (mode === 'live') flush();
  }, [mode, flush]);

  // browser crypto functions call this callback
  const tracer = useCallback((e) => push({ ...e, actor: e.actor === 'client' ? 'browser' : e.actor }), [push]);

  return (
    <Ctx.Provider value={{ shown, queue, mode, setMode, push, pushMany, operation, next, flush, clear, tracer }}>{children}</Ctx.Provider>
  );
}

export const useTrace = () => useContext(Ctx);
