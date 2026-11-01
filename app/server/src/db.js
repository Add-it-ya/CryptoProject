// MongoDB connection. The connection string comes ONLY from MONGO_URI in app/server/.env
// (local MongoDB or MongoDB Atlas). Nothing is downloaded or started automatically.
import mongoose from 'mongoose';

export let bucket = null; // GridFS bucket for ciphertext blobs

const RETRIES = Number(process.env.MONGO_RETRIES || 5);
const RETRY_DELAY_MS = 3000;

// hide user:password when printing the URI
const mask = (uri) => uri.replace(/\/\/([^@/]+)@/, '//***:***@');

// database name: MONGO_DB if set, else the one in the URI path, else "cryptovault"
function databaseName(uri) {
  if (process.env.MONGO_DB) return process.env.MONGO_DB;
  const m = uri.match(/^mongodb(?:\+srv)?:\/\/[^/]+\/([^?]+)/);
  return m && m[1] ? decodeURIComponent(m[1]) : 'cryptovault';
}

export async function connectDB() {
  const uri = (process.env.MONGO_URI || '').trim();
  if (!uri) {
    console.error(
      '\n[db] MONGO_URI is not set.\n' +
        '     Open app/server/.env and paste your MongoDB connection string, for example:\n' +
        '       MONGO_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/cryptovault\n' +
        '       MONGO_URI=mongodb://127.0.0.1:27017/cryptovault\n',
    );
    process.exit(1);
  }
  if (!/^mongodb(\+srv)?:\/\//.test(uri)) {
    console.error('[db] MONGO_URI must start with mongodb:// or mongodb+srv://');
    process.exit(1);
  }

  const dbName = databaseName(uri);
  mongoose.set('strictQuery', true);
  const conn = mongoose.connection;

  for (let attempt = 1; attempt <= RETRIES; attempt++) {
    try {
      console.log(`[db] connecting to ${mask(uri)} (database "${dbName}") - attempt ${attempt}/${RETRIES}`);
      await mongoose.connect(uri, {
        dbName,
        serverSelectionTimeoutMS: 10_000,
        connectTimeoutMS: 10_000,
        maxPoolSize: 10,
      });
      break;
    } catch (e) {
      console.error(`[db] connection failed: ${e.message}`);
      if (attempt === RETRIES) {
        console.error(
          '\n[db] Could not connect. Check that:\n' +
            '     - the URI, user name and password are correct (URL-encode special characters in the password, e.g. @ -> %40)\n' +
            "     - for MongoDB Atlas: your current IP is allowed in Network Access (or 0.0.0.0/0 for the demo)\n" +
            '     - for a local MongoDB: the mongod service is running\n',
        );
        process.exit(1);
      }
      await new Promise((r) => setTimeout(r, RETRY_DELAY_MS));
    }
  }

  // runtime events (attached after the first successful connect to keep the startup log clean)
  conn.on('disconnected', () => console.warn('[db] disconnected from MongoDB'));
  conn.on('reconnected', () => console.log('[db] reconnected to MongoDB'));
  conn.on('error', (e) => console.error('[db] error:', e.message));
  bucket = new mongoose.mongo.GridFSBucket(conn.db, { bucketName: 'blobs' });
  console.log(`[db] connected: ${conn.host} / database "${conn.name}"`);
}

export async function disconnectDB() {
  await mongoose.disconnect();
}

export const dbState = () => ['disconnected', 'connected', 'connecting', 'disconnecting'][mongoose.connection.readyState] || 'unknown';

export function putBlob(bytes, filename, metadata = {}) {
  return new Promise((resolve, reject) => {
    const up = bucket.openUploadStream(filename, { metadata });
    up.on('error', reject);
    up.on('finish', () => resolve(up.id));
    up.end(Buffer.from(bytes.buffer, bytes.byteOffset, bytes.byteLength));
  });
}

export async function getBlob(id) {
  const chunks = [];
  for await (const c of bucket.openDownloadStream(id)) chunks.push(c);
  return new Uint8Array(Buffer.concat(chunks));
}

export async function deleteBlob(id) {
  try {
    await bucket.delete(id);
  } catch {}
}
