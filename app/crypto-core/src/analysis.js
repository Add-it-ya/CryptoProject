// Statistical helpers used by the Attack Lab and the benchmarks (Shannon entropy, ECB block repetition,
// chi-square uniformity, bit-level avalanche).

/** Shannon entropy H = -sum p_i log2 p_i over byte values, in bits per byte (max 8). */
export function shannonEntropy(bytes) {
  if (!bytes.length) return 0;
  const f = new Float64Array(256);
  for (const b of bytes) f[b]++;
  let h = 0;
  for (let i = 0; i < 256; i++) {
    if (!f[i]) continue;
    const p = f[i] / bytes.length;
    h -= p * Math.log2(p);
  }
  return h;
}

/** Fraction of 16-byte blocks that are repeats of an earlier block (ECB leakage indicator). */
export function repeatedBlockRatio(bytes, block = 16) {
  const seen = new Set();
  let n = 0;
  let dup = 0;
  for (let i = 0; i + block <= bytes.length; i += block) {
    let k = '';
    for (let j = 0; j < block; j++) k += String.fromCharCode(bytes[i + j]);
    if (seen.has(k)) dup++;
    else seen.add(k);
    n++;
  }
  return n ? dup / n : 0;
}

/** Chi-square statistic of byte histogram vs uniform (255 dof; ~255 expected for random data). */
export function chiSquare(bytes) {
  const f = new Float64Array(256);
  for (const b of bytes) f[b]++;
  const e = bytes.length / 256;
  let x = 0;
  for (let i = 0; i < 256; i++) x += ((f[i] - e) * (f[i] - e)) / e;
  return x;
}

function popcount8(x) {
  x = x - ((x >> 1) & 0x55);
  x = (x & 0x33) + ((x >> 2) & 0x33);
  return (x + (x >> 4)) & 0x0f;
}

/** Fraction of differing bits between two equal-length byte arrays (avalanche measurement). */
export function bitDifference(a, b) {
  const n = Math.min(a.length, b.length);
  let d = 0;
  for (let i = 0; i < n; i++) d += popcount8(a[i] ^ b[i]);
  return d / (n * 8);
}
