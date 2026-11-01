// Live "cloud server log": every request handler records what the server RECEIVED, what it COMPUTED
// and what it STORED. The React UI subscribes over Server-Sent Events and shows it next to the
// browser-side trace, so the audience sees both ends of every operation.
const clients = new Set();
const history = [];

export function emit(evt) {
  const e = { at: Date.now(), actor: 'server', ...evt };
  history.push(e);
  if (history.length > 300) history.shift();
  const line = `data: ${JSON.stringify(e)}\n\n`;
  for (const res of clients) res.write(line);
  return e;
}

export function sseHandler(req, res) {
  res.set({ 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', Connection: 'keep-alive' });
  res.flushHeaders();
  res.write(`data: ${JSON.stringify({ actor: 'system', title: 'connected to cloud server log', at: Date.now() })}\n\n`);
  clients.add(res);
  const ping = setInterval(() => res.write(': ping\n\n'), 25000);
  req.on('close', () => {
    clearInterval(ping);
    clients.delete(res);
  });
}

export function recent() {
  return history.slice(-100);
}
