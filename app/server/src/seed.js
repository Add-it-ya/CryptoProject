// Creates the demo users exactly like the browser does (keys generated + sealed client-side),
// so the demo can start immediately. Passwords are printed on the login page.
import { generateUserKeys, exportPublicRaw, sealPrivateKeys, deriveAuthToken } from '@cryptovault/crypto-core/proposed';
import { toB64 } from '@cryptovault/crypto-core/encoding';
import User from './models/User.js';
import { createUser } from './routes/auth.js';

export const DEMO_USERS = [
  { username: 'alice', displayName: 'Alice (data owner)', password: 'Alice@Cloud2026' },
  { username: 'bob', displayName: 'Bob (recipient)', password: 'Bob@Cloud2026' },
  { username: 'charlie', displayName: 'Charlie (recipient)', password: 'Charlie@Cloud2026' },
  { username: 'mallory', displayName: 'Mallory (curious user)', password: 'Mallory@Cloud2026' },
];

export async function seedDemo() {
  if ((await User.countDocuments()) > 0) return false;
  for (const u of DEMO_USERS) {
    const keys = await generateUserKeys();
    await createUser({
      username: u.username,
      displayName: u.displayName,
      authToken: await deriveAuthToken(u.username, u.password),
      ecdhPub: toB64(await exportPublicRaw(keys.ecdh.publicKey)),
      ecdsaPub: toB64(await exportPublicRaw(keys.ecdsa.publicKey)),
      vault: await sealPrivateKeys(keys, u.password),
    });
  }
  console.log('[seed] demo users created:', DEMO_USERS.map((u) => `${u.username} / ${u.password}`).join(', '));
  return true;
}

// `npm run seed` (standalone, needs MONGO_URI)
if (process.argv[1] && process.argv[1].endsWith('seed.js')) {
  await import('./env.js');
  const { connectDB, disconnectDB } = await import('./db.js');
  await connectDB();
  const created = await seedDemo();
  console.log(created ? 'seeded' : 'database already has users - nothing to do');
  await disconnectDB();
  process.exit(0);
}
