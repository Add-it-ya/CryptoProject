import mongoose from 'mongoose';

const FileSchema = new mongoose.Schema(
  {
    scheme: { type: String, enum: ['base', 'proposed'], required: true },
    owner: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
    ownerName: String,
    // base scheme: CSP sees and stores the real file name / type
    name: String,
    mime: String,
    size: Number,
    storedSize: Number,
    gridId: mongoose.Schema.Types.ObjectId,
    backupGridId: mongoose.Schema.Types.ObjectId, // used only by the Attack Lab "restore" button
    sharedWith: [{ type: mongoose.Schema.Types.ObjectId, ref: 'User' }],
    // users removed by re-keying: they can still FETCH the new ciphertext (we let them, on purpose)
    // but cannot decrypt it - proving revocation is enforced by cryptography, not by the server.
    revoked: [{ type: mongoose.Schema.Types.ObjectId, ref: 'User' }],
    // proposed scheme
    fileId: { type: String, index: true },
    manifest: mongoose.Schema.Types.Mixed,
    signature: String,
    version: { type: Number, default: 1 },
    tampered: { type: String, default: null },
  },
  { timestamps: true },
);

export default mongoose.model('File', FileSchema);
