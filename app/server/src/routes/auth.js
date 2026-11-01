import { Router } from 'express';
import bcrypt from 'bcryptjs';
import User from '../models/User.js';
import { sign, requireAuth } from '../lib/auth.js';
import { emit } from '../lib/events.js';
import { ah, hex } from '../lib/util.js';
import { baseKeygen } from '@cryptovault/crypto-core/base';
import { fingerprint, fromB64 } from '@cryptovault/crypto-core/encoding';

const r = Router();

export async function createUser({ username, displayName, authToken, ecdhPub, ecdsaPub, vault }) {
  const base = baseKeygen(); // paper model: CSP generates the user's ECC key pair
  const user = await User.create({
    username,
    displayName: displayName || username,
    authHash: await bcrypt.hash(authToken, 10),
    ecdhPub,
    ecdsaPub,
    fingerprint: await fingerprint(fromB64(ecdhPub)),
    vault,
    basePub: Buffer.from(base.pub).toString('base64'),
    basePriv: Buffer.from(base.priv).toString('base64'),
  });
  return { user, base };
}

r.post(
  '/register',
  ah(async (req, res) => {
    const { username, displayName, authToken, ecdhPub, ecdsaPub, vault } = req.body || {};
    if (!username || !authToken || !ecdhPub || !ecdsaPub || !vault) return res.status(400).json({ error: 'missing fields' });
    if (await User.findOne({ username: username.toLowerCase() })) return res.status(409).json({ error: 'username taken' });
    const { user, base } = await createUser({ username, displayName, authToken, ecdhPub, ecdsaPub, vault });
    emit({
      user: user.username,
      route: 'POST /api/auth/register',
      title: `New user "${user.username}" registered`,
      values: {
        'received authToken (PBKDF2 of password)': authToken.slice(0, 32) + '…',
        'password received?': 'NO - only a PBKDF2 hash of it',
        'stored: bcrypt(authToken)': user.authHash.slice(0, 29) + '…',
        'stored: ECDH public key (proposed)': hex(fromB64(ecdhPub), 16),
        'stored: sealed private-key vault': `${vault.ct.length} base64 chars, opened only in the browser`,
        '[BASE] CSP generated ECC pair P = n(a)·G': hex(base.pub, 16),
      },
    });
    res.json({ token: sign(user), user: { ...user.publicView(), vault: user.vault } });
  }),
);

r.post(
  '/login',
  ah(async (req, res) => {
    const { username, authToken } = req.body || {};
    const user = await User.findOne({ username: (username || '').toLowerCase() });
    const ok = user && (await bcrypt.compare(authToken || '', user.authHash));
    emit({
      user: username,
      route: 'POST /api/auth/login',
      title: ok ? `Login OK for "${username}" - sending back the SEALED key vault` : `Login FAILED for "${username}"`,
      values: ok ? { 'bcrypt check': 'match', 'vault sent (still encrypted)': `salt ${user.vault.salt}, ${user.vault.iter} PBKDF2 iterations` } : {},
    });
    if (!ok) return res.status(401).json({ error: 'invalid username or password' });
    res.json({ token: sign(user), user: { ...user.publicView(), vault: user.vault } });
  }),
);

r.get('/me', requireAuth, (req, res) => res.json({ user: { ...req.user.publicView(), vault: req.user.vault } }));

export default r;
