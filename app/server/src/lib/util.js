import { shannonEntropy, repeatedBlockRatio } from '@cryptovault/crypto-core/analysis';

export const hex = (b, n = 32) => {
  const h = Buffer.from(b).toString('hex');
  return h.length > n * 2 ? h.slice(0, n * 2) + `… (${b.length} B)` : h;
};
export const ascii = (b, n = 48) =>
  Array.from(b.subarray(0, n))
    .map((c) => (c >= 32 && c < 127 ? String.fromCharCode(c) : '·'))
    .join('');
export function stats(bytes) {
  return {
    entropy: +shannonEntropy(bytes).toFixed(4),
    repeatedBlocksPct: +(100 * repeatedBlockRatio(bytes)).toFixed(2),
  };
}
export const ah = (fn) => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);
