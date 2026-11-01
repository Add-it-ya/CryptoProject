import './env.js';
import { connectDB, disconnectDB } from './db.js';
import { createApp } from './app.js';
import { seedDemo } from './seed.js';

const PORT = Number(process.env.PORT || 5000);
await connectDB();
if ((process.env.SEED_DEMO ?? 'true') !== 'false') await seedDemo();
const server = createApp().listen(PORT, () => {
  console.log(`\n  CryptoVault  ->  http://localhost:${PORT}   (API health: /api/health)\n`);
});

async function shutdown(sig) {
  console.log(`\n[server] ${sig} received, closing...`);
  server.close();
  await disconnectDB();
  process.exit(0);
}
process.on('SIGINT', () => shutdown('SIGINT'));
process.on('SIGTERM', () => shutdown('SIGTERM'));
