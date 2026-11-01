import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSession } from '../lib/session.jsx';
import Inspector from '../components/Inspector.jsx';

const DEMO = [
  ['alice', 'Alice@Cloud2026', 'data owner'],
  ['bob', 'Bob@Cloud2026', 'recipient'],
  ['charlie', 'Charlie@Cloud2026', 'recipient'],
  ['mallory', 'Mallory@Cloud2026', 'curious user'],
];

// Shannon entropy of the password's own characters (Unit 2) + the usual charset estimate
function pwEntropy(pw) {
  if (!pw) return { shannon: 0, charset: 0 };
  const f = {};
  for (const c of pw) f[c] = (f[c] || 0) + 1;
  let h = 0;
  for (const k in f) {
    const p = f[k] / pw.length;
    h -= p * Math.log2(p);
  }
  let n = 0;
  if (/[a-z]/.test(pw)) n += 26;
  if (/[A-Z]/.test(pw)) n += 26;
  if (/[0-9]/.test(pw)) n += 10;
  if (/[^a-zA-Z0-9]/.test(pw)) n += 33;
  return { shannon: h * pw.length, perChar: h, charset: pw.length * Math.log2(n || 1) };
}

export default function Login() {
  const { login, register } = useSession();
  const nav = useNavigate();
  const [tab, setTab] = useState('login');
  const [username, setU] = useState('alice');
  const [displayName, setD] = useState('');
  const [password, setP] = useState('Alice@Cloud2026');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const e = pwEntropy(password);

  const go = async (ev) => {
    ev.preventDefault();
    setBusy(true);
    setErr('');
    try {
      if (tab === 'login') await login(username, password);
      else await register(username, displayName || username, password);
      nav('/');
    } catch (x) {
      setErr(x.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-wrap">
      <div className="login-card">
        <div className="brand big">
          <img src="/favicon.svg" alt="" />
          <div>
            <b>CryptoVault</b>
            <small>Secure Cloud File Sharing Using Hybrid Cryptography - Group 18</small>
          </div>
        </div>
        <div className="tabs">
          <button className={tab === 'login' ? 'on' : ''} onClick={() => setTab('login')}>
            Log in
          </button>
          <button className={tab === 'register' ? 'on' : ''} onClick={() => setTab('register')}>
            Register
          </button>
        </div>
        <form onSubmit={go}>
          <label>Username</label>
          <input value={username} onChange={(x) => setU(x.target.value)} autoComplete="username" />
          {tab === 'register' && (
            <>
              <label>Display name</label>
              <input value={displayName} onChange={(x) => setD(x.target.value)} />
            </>
          )}
          <label>Password</label>
          <input type="password" value={password} onChange={(x) => setP(x.target.value)} autoComplete="current-password" />
          {tab === 'register' && (
            <div className="pw-meter">
              <div>
                Shannon entropy: <b>{e.shannon.toFixed(1)} bits</b> <small>({(e.perChar || 0).toFixed(2)} bits/char × {password.length})</small>
              </div>
              <div>
                Charset estimate: <b>{e.charset.toFixed(1)} bits</b>
              </div>
              <div className="ebar">
                <div style={{ width: Math.min(100, e.charset) + '%', background: e.charset > 60 ? 'var(--green)' : e.charset > 40 ? 'var(--amber)' : 'var(--red)' }} />
              </div>
            </div>
          )}
          {err && <div className="alert red">{err}</div>}
          <button className="btn primary full" disabled={busy}>
            {busy ? 'Working… (PBKDF2 600k iterations)' : tab === 'login' ? 'Log in' : 'Create account + generate keys'}
          </button>
        </form>
        <div className="demo-users">
          <small>Demo accounts (open a second browser window for another user):</small>
          <div>
            {DEMO.map(([u, p, r]) => (
              <button
                key={u}
                className="chip"
                onClick={() => {
                  setTab('login');
                  setU(u);
                  setP(p);
                }}
              >
                {u} <small>{r}</small>
              </button>
            ))}
          </div>
        </div>
      </div>
      <div className="login-insp">
        <Inspector />
      </div>
    </div>
  );
}
