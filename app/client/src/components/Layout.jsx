import { NavLink, Outlet, Navigate } from 'react-router-dom';
import { useSession } from '../lib/session.jsx';
import Inspector from './Inspector.jsx';

export default function Layout() {
  const { user, keys, logout } = useSession();
  if (!user || !keys) return <Navigate to="/login" replace />;
  return (
    <div className="shell">
      <header className="top">
        <div className="brand">
          <img src="/favicon.svg" alt="" />
          <div>
            <b>CryptoVault</b>
            <small>Secure Cloud File Sharing · Group 18</small>
          </div>
        </div>
        <nav>
          <NavLink to="/">Files</NavLink>
          <NavLink to="/lab">Attack Lab</NavLink>
          <NavLink to="/cloud">What the Cloud Sees</NavLink>
          <NavLink to="/results">Results</NavLink>
        </nav>
        <div className="who">
          <div>
            <b>{user.displayName}</b>
            <small title="SHA-256 fingerprint of my ECDH public key - compare out-of-band">🔑 {user.fingerprint.slice(0, 19)}</small>
          </div>
          <button className="btn sm ghost" onClick={logout}>
            Log out
          </button>
        </div>
      </header>
      <div className="main">
        <section className="page">
          <Outlet />
        </section>
        <Inspector />
      </div>
    </div>
  );
}
