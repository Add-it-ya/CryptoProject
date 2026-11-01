import { Router } from 'express';
import User from '../models/User.js';
import { requireAuth } from '../lib/auth.js';
import { ah } from '../lib/util.js';

const r = Router();
// Public key directory: anyone logged in can read everybody's PUBLIC keys (by design).
r.get(
  '/',
  requireAuth,
  ah(async (req, res) => {
    const users = await User.find().sort({ username: 1 });
    res.json(users.map((u) => u.publicView()));
  }),
);
export default r;
