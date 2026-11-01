import jwt from 'jsonwebtoken';
import User from '../models/User.js';

const SECRET = () => process.env.JWT_SECRET || 'group18-dev-secret';

export function sign(user) {
  return jwt.sign({ sub: String(user._id), u: user.username }, SECRET(), { expiresIn: '8h' });
}

export async function requireAuth(req, res, next) {
  const h = req.headers.authorization || '';
  const tok = h.startsWith('Bearer ') ? h.slice(7) : req.query.token;
  try {
    const p = jwt.verify(tok, SECRET());
    req.user = await User.findById(p.sub);
    if (!req.user) throw new Error('no user');
    next();
  } catch {
    res.status(401).json({ error: 'Not authenticated' });
  }
}
