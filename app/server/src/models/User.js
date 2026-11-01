import mongoose from 'mongoose';

const UserSchema = new mongoose.Schema(
  {
    username: { type: String, required: true, unique: true, lowercase: true, trim: true },
    displayName: { type: String, required: true },
    // bcrypt( PBKDF2(password) ) - the server never sees the password itself
    authHash: { type: String, required: true },
    // PROPOSED scheme: public keys only (private keys stay sealed in the vault, opened in the browser)
    ecdhPub: { type: String, required: true },
    ecdsaPub: { type: String, required: true },
    fingerprint: { type: String, required: true },
    vault: { kdf: String, iter: Number, salt: String, iv: String, ct: String },
    // BASE scheme (Rehman et al.): the CSP generates and holds the ECC key pair (Fig. 3 / Fig. 5)
    basePub: { type: String, required: true },
    basePriv: { type: String, required: true },
  },
  { timestamps: true },
);

UserSchema.methods.publicView = function () {
  return {
    id: String(this._id),
    username: this.username,
    displayName: this.displayName,
    ecdhPub: this.ecdhPub,
    ecdsaPub: this.ecdsaPub,
    fingerprint: this.fingerprint,
    basePub: this.basePub,
  };
};

export default mongoose.model('User', UserSchema);
