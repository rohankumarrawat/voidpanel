/**
 * VoidPanel WhatsApp Web Microservice — Multi-Session Edition
 * ===========================================================
 * Self-hosted, multi-tenant WhatsApp session manager using @whiskeysockets/baileys.
 * Each panel user gets their OWN session, QR code, and inbox.
 *
 * All endpoints accept ?session=<sessionId> (GET) or { session: <sessionId> } (POST body).
 * sessionId convention: "<domain>__<username>"  e.g. "ranjaka.com__admin"
 *
 * Endpoints:
 *   GET  /qr               → Returns QR for ?session=<id>
 *   GET  /status           → Returns { state } for ?session=<id>
 *   POST /logout           → Clears session for { session }
 *   GET  /incoming         → Drains incoming message queue for ?session=<id>
 *   POST /send             → Sends text message via { session, to, message }
 *   POST /send-media       → Sends media via { session, to, mediaBase64, … }
 *   POST /broadcast        → Sends to multiple contacts { session, contacts, message }
 *   GET  /health           → Health check (lists active sessions)
 *
 * Run: node server.js
 * Port: 3001 (localhost only, proxied by Django)
 */

import makeWASocket, {
  useMultiFileAuthState,
  DisconnectReason,
  fetchLatestBaileysVersion,
  makeCacheableSignalKeyStore,
  isJidBroadcast,
} from '@whiskeysockets/baileys';
import express from 'express';
import cors from 'cors';
import QRCode from 'qrcode';
import pino from 'pino';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const AUTH_BASE = path.join(__dirname, 'auth_sessions'); // plural — one subfolder per session
const PORT = 3001;

const logger = pino({ level: 'silent' });

// ── Per-session state store ────────────────────────────────────────────────────
// sessions Map: sessionId → { state, socket, qr, reconnectTimer, incomingQueue, receiptsQueue }
const sessions = new Map();

// Helper: get or create session entry (does NOT start connection)
function getSession(id) {
  if (!sessions.has(id)) {
    sessions.set(id, {
      state: 'idle',      // idle | connecting | qr_ready | connected | disconnected | logged_out
      socket: null,
      qr: null,           // base64 PNG (raw, no prefix)
      reconnectTimer: null,
      incomingQueue: [],
      receiptsQueue: [],
    });
  }
  return sessions.get(id);
}

// Sanitize sessionId to safe directory name
function safeId(id) {
  return String(id).replace(/[^a-zA-Z0-9._-]/g, '_').slice(0, 120);
}

function authDir(sessionId) {
  return path.join(AUTH_BASE, safeId(sessionId));
}

// ── Express App ────────────────────────────────────────────────────────────────
const app = express();
app.use(cors({ origin: ['http://localhost', 'http://127.0.0.1'] }));
app.use(express.json({ limit: '10mb' }));

// ── Health check ───────────────────────────────────────────────────────────────
app.get('/health', (req, res) => {
  const active = [];
  for (const [id, s] of sessions) {
    active.push({ id, state: s.state });
  }
  res.json({ ok: true, sessions: active });
});

// ── QR endpoint ───────────────────────────────────────────────────────────────
app.get('/qr', async (req, res) => {
  const sessionId = req.query.session;
  if (!sessionId) return res.status(400).json({ error: '?session= is required' });

  const s = getSession(sessionId);

  if (s.state === 'connected') {
    return res.json({ state: 'connected', qr: null });
  }

  if (!s.qr) {
    // Auto-start if idle or disconnected
    if (s.state === 'idle' || s.state === 'disconnected') {
      startSession(sessionId);
    }
    return res.json({ state: s.state, qr: null, message: 'Initializing...' });
  }

  return res.json({ state: 'qr_ready', qr: s.qr });
});

// ── Status endpoint ────────────────────────────────────────────────────────────
app.get('/status', (req, res) => {
  const sessionId = req.query.session;
  if (!sessionId) return res.status(400).json({ error: '?session= is required' });
  const s = getSession(sessionId);
  res.json({ state: s.state });
});

// ── Logout endpoint ────────────────────────────────────────────────────────────
app.post('/logout', async (req, res) => {
  const sessionId = req.body?.session;
  if (!sessionId) return res.status(400).json({ error: '`session` is required in body' });

  if (!sessions.has(sessionId)) {
    return res.json({ ok: true, message: 'No active session.' });
  }

  const s = sessions.get(sessionId);

  try {
    if (s.socket) await s.socket.logout();
  } catch (_) {}

  if (s.reconnectTimer) clearTimeout(s.reconnectTimer);

  // Remove auth files
  const dir = authDir(sessionId);
  if (fs.existsSync(dir)) fs.rmSync(dir, { recursive: true, force: true });

  sessions.delete(sessionId);
  res.json({ ok: true, message: 'Logged out and session cleared.' });
});

// ── Incoming messages poll ─────────────────────────────────────────────────────
app.get('/incoming', (req, res) => {
  const sessionId = req.query.session;
  if (!sessionId) return res.status(400).json({ error: '?session= is required' });

  const s = getSession(sessionId);
  const msgs = [...s.incomingQueue];
  s.incomingQueue.length = 0;
  const receipts = [...s.receiptsQueue];
  s.receiptsQueue.length = 0;
  res.json({ messages: msgs, receipts });
});

// ── Send text ──────────────────────────────────────────────────────────────────
app.post('/send', async (req, res) => {
  const { session: sessionId, to, message } = req.body;
  if (!sessionId) return res.status(400).json({ ok: false, error: '`session` is required' });

  const s = sessions.get(sessionId);
  if (!s || s.state !== 'connected' || !s.socket) {
    return res.status(503).json({ ok: false, error: 'WhatsApp not connected for this session. Scan QR first.' });
  }

  if (!to || !message) {
    return res.status(400).json({ ok: false, error: '`to` and `message` are required.' });
  }

  const digits = String(to).replace(/\D/g, '');
  const jid = digits.includes('@') ? digits : `${digits}@s.whatsapp.net`;

  try {
    const result = await s.socket.sendMessage(jid, { text: message });
    return res.json({ ok: true, messageId: result?.key?.id, to: jid });
  } catch (err) {
    return res.status(500).json({ ok: false, error: err.message });
  }
});

// ── Broadcast ──────────────────────────────────────────────────────────────────
app.post('/broadcast', async (req, res) => {
  const { session: sessionId, contacts, message } = req.body;
  if (!sessionId) return res.status(400).json({ ok: false, error: '`session` is required' });

  const s = sessions.get(sessionId);
  if (!s || s.state !== 'connected' || !s.socket) {
    return res.status(503).json({ ok: false, error: 'WhatsApp not connected for this session.' });
  }

  if (!contacts || !Array.isArray(contacts) || !message) {
    return res.status(400).json({ ok: false, error: '`contacts` array and `message` required.' });
  }

  const results = [];
  for (const to of contacts) {
    const digits = String(to).replace(/\D/g, '');
    const jid = `${digits}@s.whatsapp.net`;
    try {
      const r = await s.socket.sendMessage(jid, { text: message });
      results.push({ to, ok: true, messageId: r?.key?.id });
      await new Promise(resolve => setTimeout(resolve, 800));
    } catch (err) {
      results.push({ to, ok: false, error: err.message });
    }
  }

  const sent = results.filter(r => r.ok).length;
  return res.json({ ok: true, sent, failed: contacts.length - sent, results });
});

// ── Send media ─────────────────────────────────────────────────────────────────
app.post('/send-media', async (req, res) => {
  const { session: sessionId, to, mediaBase64, mimeType, caption, filename } = req.body;
  if (!sessionId) return res.status(400).json({ ok: false, error: '`session` is required' });

  const s = sessions.get(sessionId);
  if (!s || s.state !== 'connected' || !s.socket) {
    return res.status(503).json({ ok: false, error: 'WhatsApp not connected for this session.' });
  }

  if (!to || !mediaBase64 || !mimeType) {
    return res.status(400).json({ ok: false, error: '`to`, `mediaBase64`, and `mimeType` are required.' });
  }

  const digits = String(to).replace(/\D/g, '');
  const jid = `${digits}@s.whatsapp.net`;
  const buffer = Buffer.from(mediaBase64, 'base64');

  try {
    let msgPayload;
    if (mimeType.startsWith('image/')) {
      msgPayload = { image: buffer, caption: caption || '', mimetype: mimeType };
    } else if (mimeType.startsWith('video/')) {
      msgPayload = { video: buffer, caption: caption || '', mimetype: mimeType };
    } else {
      msgPayload = { document: buffer, mimetype: mimeType, fileName: filename || 'file', caption: caption || '' };
    }
    const result = await s.socket.sendMessage(jid, msgPayload);
    return res.json({ ok: true, messageId: result?.key?.id });
  } catch (err) {
    return res.status(500).json({ ok: false, error: err.message });
  }
});

// ── Session Connection Logic ───────────────────────────────────────────────────
async function startSession(sessionId) {
  const s = getSession(sessionId);

  if (s.state === 'connecting' || s.state === 'connected') return;

  s.state = 'connecting';
  s.qr = null;

  const dir = authDir(sessionId);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

  const { state, saveCreds } = await useMultiFileAuthState(dir);
  const { version } = await fetchLatestBaileysVersion();

  const sock = makeWASocket({
    version,
    logger,
    printQRInTerminal: false,
    auth: {
      creds: state.creds,
      keys: makeCacheableSignalKeyStore(state.keys, logger),
    },
    generateHighQualityLinkPreview: false,
    shouldIgnoreJid: jid => isJidBroadcast(jid),
    getMessage: async () => undefined,
  });

  s.socket = sock;

  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('connection.update', async (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      try {
        let qrDataUrl = await QRCode.toDataURL(qr, {
          errorCorrectionLevel: 'M',
          type: 'image/png',
          width: 280,
          margin: 2,
          color: { dark: '#000000', light: '#ffffff' },
        });
        s.qr = qrDataUrl.replace('data:image/png;base64,', '');
        s.state = 'qr_ready';
        console.log(`[WA][${sessionId}] QR code ready.`);
      } catch (err) {
        console.error(`[WA][${sessionId}] QR generation error:`, err.message);
      }
    }

    if (connection === 'open') {
      s.state = 'connected';
      s.qr = null;
      console.log(`[WA][${sessionId}] ✅ Connected!`);
    }

    if (connection === 'close') {
      const statusCode = lastDisconnect?.error?.output?.statusCode;
      const shouldReconnect = statusCode !== DisconnectReason.loggedOut;

      console.log(`[WA][${sessionId}] Connection closed. Code: ${statusCode}. Reconnect: ${shouldReconnect}`);

      s.state = shouldReconnect ? 'disconnected' : 'logged_out';
      s.qr = null;
      s.socket = null;

      if (shouldReconnect) {
        s.reconnectTimer = setTimeout(() => {
          console.log(`[WA][${sessionId}] Reconnecting...`);
          startSession(sessionId);
        }, 5000);
      } else {
        // Logged out — wipe auth files
        const dir = authDir(sessionId);
        if (fs.existsSync(dir)) fs.rmSync(dir, { recursive: true, force: true });
        s.state = 'idle';
      }
    }
  });

  // Incoming messages
  sock.ev.on('messages.upsert', async ({ messages: msgs, type }) => {
    if (type !== 'notify') return;

    for (const msg of msgs) {
      if (msg.key.fromMe) continue;

      const from = msg.key.remoteJid || '';
      const phone = from.replace('@s.whatsapp.net', '').replace('@c.us', '');
      const text = msg.message?.conversation
        || msg.message?.extendedTextMessage?.text
        || msg.message?.imageMessage?.caption
        || '';
      const name = msg.pushName || phone;
      const ts = msg.messageTimestamp
        ? new Date(Number(msg.messageTimestamp) * 1000).toISOString()
        : new Date().toISOString();

      const entry = { from, phone, name, text, timestamp: ts, type: 'incoming' };
      s.incomingQueue.push(entry);
      if (s.incomingQueue.length > 200) s.incomingQueue.shift();
      console.log(`[WA][${sessionId}] ← ${name} (${phone}): ${text.slice(0, 50)}`);
    }
  });

  // Read receipts
  sock.ev.on('message-receipt.update', updates => {
    for (const { key, receipt } of updates) {
      if (receipt?.readTimestamp) {
        s.receiptsQueue.push({
          messageId: key.id,
          phone: (key.remoteJid || '').replace('@s.whatsapp.net', '').replace('@c.us', ''),
          timestamp: new Date(Number(receipt.readTimestamp) * 1000).toISOString(),
        });
        if (s.receiptsQueue.length > 500) s.receiptsQueue.shift();
      }
    }
  });
}

// ── Startup — resume any existing sessions found on disk ──────────────────────
app.listen(PORT, '127.0.0.1', () => {
  console.log(`[VoidPanel WA Service] Multi-session mode — Running on http://127.0.0.1:${PORT}`);

  if (!fs.existsSync(AUTH_BASE)) {
    fs.mkdirSync(AUTH_BASE, { recursive: true });
    console.log('[WA] No existing sessions found.');
    return;
  }

  const dirs = fs.readdirSync(AUTH_BASE, { withFileTypes: true })
    .filter(d => d.isDirectory())
    .map(d => d.name);

  if (dirs.length === 0) {
    console.log('[WA] No existing sessions. Waiting for QR requests...');
    return;
  }

  for (const sessionId of dirs) {
    console.log(`[WA] Resuming existing session: ${sessionId}`);
    startSession(sessionId);
  }
});
