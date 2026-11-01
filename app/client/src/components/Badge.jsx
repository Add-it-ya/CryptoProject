export function SchemeBadge({ scheme }) {
  return scheme === 'base' ? <span className="badge red">BASE · AES-ECC</span> : <span className="badge green">PROPOSED · GCM+ECDH+ECDSA</span>;
}
export function EntropyBar({ value }) {
  const pct = Math.max(0, Math.min(100, (value / 8) * 100));
  const col = value > 7.9 ? 'var(--green)' : value > 6 ? 'var(--amber)' : 'var(--red)';
  return (
    <div className="ebar" title={`${value} bits/byte`}>
      <div style={{ width: pct + '%', background: col }} />
      <span>{value.toFixed(3)}</span>
    </div>
  );
}
