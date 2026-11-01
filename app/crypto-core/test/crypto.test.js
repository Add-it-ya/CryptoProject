import { test } from 'node:test';
import assert from 'node:assert/strict';
import { baseKeygen, baseEncrypt, baseDecrypt, publicKeyAttack } from '../src/base_aes_ecc.js';
import {
  generateUserKeys,
  exportPublicRaw,
  encryptFile,
  decryptFile,
  addRecipient,
  rekeyFile,
  sealPrivateKeys,
  openPrivateKeys,
  publicKeyAttackOnProposed,
  IntegrityError,
  AccessError,
  CHUNK_SIZE,
} from '../src/proposed_ahe.js';
import { randomBytes, te, td, bytesEqual } from '../src/encoding.js';
import { shannonEntropy, repeatedBlockRatio } from '../src/analysis.js';

async function mkUser(id) {
  const keys = await generateUserKeys();
  return {
    userId: id,
    label: id,
    keys,
    ecdhPub: await exportPublicRaw(keys.ecdh.publicKey),
    ecdsaPub: await exportPublicRaw(keys.ecdsa.publicKey),
    me: { userId: id, ecdhPriv: keys.ecdh.privateKey },
  };
}

test('base scheme round-trips and is broken by the public-key attack', () => {
  const { pub } = baseKeygen();
  const msg = te.encode('Salary sheet: Alice 120000, Bob 95000. Confidential.');
  const ct = baseEncrypt(msg, pub);
  assert.ok(bytesEqual(baseDecrypt(ct, pub), msg));
  // attacker only knows the PUBLIC key
  assert.equal(td.decode(publicKeyAttack(ct, pub)), td.decode(msg));
});

test('base scheme is deterministic and leaks repeated blocks (ECB)', () => {
  const { pub } = baseKeygen();
  const msg = new Uint8Array(16 * 64).fill(0x41);
  const c1 = baseEncrypt(msg, pub);
  const c2 = baseEncrypt(msg, pub);
  assert.ok(bytesEqual(c1, c2));
  assert.ok(repeatedBlockRatio(c1) > 0.9);
});

test('base scheme: block swap goes completely undetected', () => {
  const { pub } = baseKeygen();
  const msg = te.encode('PAY 00100 RUPEES TO ALICE.......PAY 99999 RUPEES TO MALLORY.....');
  const ct = baseEncrypt(msg, pub);
  const t = ct.slice();
  t.set(ct.subarray(32, 48), 0);
  t.set(ct.subarray(0, 16), 32);
  const out = baseDecrypt(t, pub); // no error raised
  assert.ok(td.decode(out).startsWith('PAY 99999 RUPEES'));
});

test('proposed scheme: round trip (multi-chunk), sharing, tamper detection, attacks, revocation', async () => {
  const alice = await mkUser('alice');
  const bob = await mkUser('bob');
  const carol = await mkUser('carol');
  const plain = randomBytes(CHUNK_SIZE * 2 + 1234);
  const info = { fileId: 'f1', ownerId: 'alice', version: 1, name: 'report.pdf', mime: 'application/pdf' };
  const steps = [];
  const { ciphertext, manifest, signature } = await encryptFile(
    plain,
    info,
    [alice, bob].map((u) => ({ userId: u.userId, ecdhPub: u.ecdhPub, label: u.label })),
    alice.keys.ecdsa.privateKey,
    undefined,
    (s) => steps.push(s),
  );
  assert.ok(steps.length >= 5);
  assert.equal(manifest.chunks, 3);
  assert.ok(shannonEntropy(ciphertext) > 7.99);

  const r = await decryptFile(ciphertext, manifest, signature, bob.me, alice.ecdsaPub);
  assert.ok(bytesEqual(r.plain, plain));
  assert.equal(r.meta.name, 'report.pdf');

  // carol is not a recipient
  await assert.rejects(decryptFile(ciphertext, manifest, signature, carol.me, alice.ecdsaPub), AccessError);

  // single bit flip in ciphertext
  const t = ciphertext.slice();
  t[100] ^= 1;
  await assert.rejects(decryptFile(t, manifest, signature, bob.me, alice.ecdsaPub), IntegrityError);
  // attacker also patches the hash in the manifest -> signature breaks
  const m2 = { ...manifest, ctHash: '00'.repeat(32) };
  await assert.rejects(decryptFile(ciphertext, m2, signature, bob.me, alice.ecdsaPub), IntegrityError);
  // attacker re-signs with own key -> still rejected against alice's real public key
  const mallory = await mkUser('mallory');
  const forged = await encryptFile(te.encode('evil'), { ...info }, [{ userId: 'bob', ecdhPub: bob.ecdhPub }], mallory.keys.ecdsa.privateKey);
  await assert.rejects(decryptFile(forged.ciphertext, forged.manifest, forged.signature, bob.me, alice.ecdsaPub), IntegrityError);

  // public-key attack fails
  const att = await publicKeyAttackOnProposed(ciphertext, manifest, [alice.ecdhPub, bob.ecdhPub, alice.ecdsaPub, bob.ecdsaPub]);
  assert.equal(att.success, false);

  // share with carol without re-encrypting
  const shared = await addRecipient(manifest, alice.me, { userId: 'carol', ecdhPub: carol.ecdhPub }, alice.keys.ecdsa.privateKey);
  const rc = await decryptFile(ciphertext, shared.manifest, shared.signature, carol.me, alice.ecdsaPub);
  assert.ok(bytesEqual(rc.plain, plain));

  // revoke bob: re-key to v2 for alice + carol only
  const v2 = await rekeyFile(
    ciphertext,
    shared.manifest,
    shared.signature,
    alice.me,
    alice.ecdsaPub,
    [alice, carol].map((u) => ({ userId: u.userId, ecdhPub: u.ecdhPub })),
    alice.keys.ecdsa.privateKey,
  );
  assert.equal(v2.manifest.version, 2);
  await assert.rejects(decryptFile(v2.ciphertext, v2.manifest, v2.signature, bob.me, alice.ecdsaPub), AccessError);
  // bob's OLD wrapped entry relabelled into v2 manifest does not open v2 (AAD binds version)
  const bobOld = manifest.recipients.find((x) => x.userId === 'bob');
  const smuggled = { ...v2.manifest, recipients: [...v2.manifest.recipients, bobOld] };
  await assert.rejects(decryptFile(v2.ciphertext, smuggled, v2.signature, bob.me, alice.ecdsaPub), IntegrityError);
});

test('key vault: right password opens, wrong password fails', async () => {
  const k = await generateUserKeys();
  const vault = await sealPrivateKeys(k, 'correct horse battery staple', 1000);
  const opened = await openPrivateKeys(vault, 'correct horse battery staple');
  assert.ok(opened.ecdhPriv && opened.ecdsaPriv);
  await assert.rejects(openPrivateKeys(vault, 'wrong'), AccessError);
});
