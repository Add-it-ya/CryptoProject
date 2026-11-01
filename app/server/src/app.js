import express from 'express';
import cors from 'cors';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import authRoutes from './routes/auth.js';
import userRoutes from './routes/users.js';
import fileRoutes from './routes/files.js';
import labRoutes from './routes/lab.js';
import { sseHandler, recent } from './lib/events.js';
import { dbState } from './db.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));

export function createApp() {
  const app = express();
  app.use(cors());
  app.use(express.json({ limit: '4mb' }));

  app.get('/api/health', (req, res) => res.json({ ok: true, app: 'CryptoVault - Group 18', db: dbState() }));
  app.get('/api/events', sseHandler); // live cloud-server log (Server-Sent Events)
  app.get('/api/events/recent', (req, res) => res.json(recent()));
  app.use('/api/auth', authRoutes);
  app.use('/api/users', userRoutes);
  app.use('/api/files', fileRoutes);
  app.use('/api/lab', labRoutes);
  app.get('/api/bench', (req, res) => {
    const p = path.join(HERE, '..', '..', 'bench', 'results', 'results.json');
    if (!fs.existsSync(p)) return res.status(404).json({ error: 'run "npm run bench" first' });
    res.type('application/json').send(fs.readFileSync(p));
  });

  // production: serve the built React client
  const dist = path.join(HERE, '..', '..', 'client', 'dist');
  if (fs.existsSync(dist)) {
    app.use(express.static(dist));
    app.get(/^\/(?!api\/).*/, (req, res) => res.sendFile(path.join(dist, 'index.html')));
  }

  app.use((err, req, res, next) => {
    console.error(err);
    res.status(500).json({ error: err.message || 'server error' });
  });
  return app;
}
