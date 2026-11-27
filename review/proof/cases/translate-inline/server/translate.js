'use strict';

const fs = require('node:fs');
const path = require('node:path');
const https = require('node:https');

const HOST = 'api.lingvo.example.invalid';
const MAX_TEXT = 4000;
const MAX_CONTEXT = 2000;
const TIMEOUT_MS = 15000;
const LANG = /^[a-z]{2,3}(-[A-Za-z0-9]{2,8})?$/;

class TranslateError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

function keysFile() {
  if (process.env.LOAM_PLUGIN_KEYS) return process.env.LOAM_PLUGIN_KEYS;
  if (process.env.LOAM_PLUGIN_PRIVATE) return path.join(process.env.LOAM_PLUGIN_PRIVATE, 'keys.env');
  return null;
}

function readKey() {
  const file = keysFile();
  if (!file) return null;
  let text;
  try {
    text = fs.readFileSync(file, 'utf8');
  } catch {
    return null;
  }
  for (const line of text.split('\n')) {
    const eq = line.indexOf('=');
    if (eq < 1 || line.slice(0, eq).trim() !== 'LINGVO_API_KEY') continue;
    const value = line.slice(eq + 1).trim().replace(/^['"]|['"]$/g, '');
    return value || null;
  }
  return null;
}

function hasKey() {
  return Boolean(readKey());
}

function clean(payload) {
  const text = payload && typeof payload.text === 'string' ? payload.text.trim() : '';
  if (!text) throw new TranslateError(400, 'Select a passage to translate first.');
  if (text.length > MAX_TEXT) throw new TranslateError(413, 'That passage is too long. Select a shorter part.');
  const target = typeof payload.target === 'string' && LANG.test(payload.target) ? payload.target : 'en';
  const context = typeof payload.context === 'string' ? payload.context.slice(-MAX_CONTEXT) : '';
  return { text, target, context };
}

function post(body, key) {
  const data = JSON.stringify(body);
  return new Promise((resolve, reject) => {
    const req = https.request(
      {
        host: HOST,
        path: '/v1/translate',
        method: 'POST',
        timeout: TIMEOUT_MS,
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(data),
          Accept: 'application/json',
          Authorization: `Bearer ${key}`,
        },
      },
      (res) => {
        const chunks = [];
        res.on('data', (c) => chunks.push(c));
        res.on('end', () => {
          const status = res.statusCode || 0;
          if (status === 401 || status === 403) {
            reject(new TranslateError(401, 'Lingvo did not accept your key. Check it in Settings › Connections › API keys.'));
            return;
          }
          if (status === 429) {
            reject(new TranslateError(429, 'Lingvo is busy right now. Try again in a minute.'));
            return;
          }
          if (status < 200 || status >= 300) {
            reject(new TranslateError(502, 'Lingvo could not translate that just now. Try again.'));
            return;
          }
          try {
            resolve(JSON.parse(Buffer.concat(chunks).toString('utf8')));
          } catch {
            reject(new TranslateError(502, 'Lingvo sent an answer that could not be read.'));
          }
        });
      },
    );
    req.on('timeout', () => req.destroy(new TranslateError(504, 'Lingvo took too long to answer. Try again.')));
    req.on('error', (err) => {
      if (err instanceof TranslateError) reject(err);
      else reject(new TranslateError(502, 'Lingvo could not be reached. Try again shortly.'));
    });
    req.end(data);
  });
}

async function translate(payload) {
  const { text, target, context } = clean(payload);
  const key = readKey();
  if (!key) throw new TranslateError(409, 'Add your Lingvo key in Settings › Connections › API keys to translate.');
  const reply = await post({ text, target, context }, key);
  const translation = reply && typeof reply.translation === 'string' ? reply.translation : '';
  if (!translation) throw new TranslateError(502, 'Lingvo answered without a translation. Try again.');
  return {
    translation,
    detected: typeof reply.detected === 'string' ? reply.detected : null,
    target,
  };
}

module.exports = { translate, hasKey, TranslateError };
