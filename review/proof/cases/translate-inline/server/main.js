'use strict';

const http = require('node:http');
const { translate, hasKey, TranslateError } = require('./translate.js');

const PORT = Number(process.env.PORT || process.env.LOAM_PLUGIN_PORT || 0);
const MAX_BODY = 64 * 1024;

function send(res, status, body) {
  const data = JSON.stringify(body);
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(data),
    'Cache-Control': 'no-store',
  });
  res.end(data);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    let tooLarge = false;
    req.on('data', (chunk) => {
      size += chunk.length;
      if (size > MAX_BODY) {
        tooLarge = true;
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', () => {
      if (tooLarge) reject(new TranslateError(413, 'That passage is too long to translate in one go.'));
      else resolve(Buffer.concat(chunks).toString('utf8'));
    });
    req.on('error', reject);
  });
}

const server = http.createServer(async (req, res) => {
  const path = new URL(req.url, 'http://127.0.0.1').pathname;
  try {
    if (req.method === 'GET' && path === '/status') {
      send(res, 200, { ok: true, key: hasKey() });
      return;
    }
    if (req.method === 'POST' && path === '/translate') {
      const raw = await readBody(req);
      let payload;
      try {
        payload = JSON.parse(raw);
      } catch {
        throw new TranslateError(400, 'The request could not be read.');
      }
      send(res, 200, await translate(payload));
      return;
    }
    send(res, 404, { error: 'Nothing here.' });
  } catch (err) {
    if (err instanceof TranslateError) {
      send(res, err.status, { error: err.message });
      return;
    }
    console.error('translate-inline: unexpected error', err);
    send(res, 500, { error: 'Something went wrong translating that. Try again in a moment.' });
  }
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`translate-inline listening on 127.0.0.1:${server.address().port}`);
});

for (const signal of ['SIGTERM', 'SIGINT']) {
  process.on(signal, () => server.close(() => process.exit(0)));
}
