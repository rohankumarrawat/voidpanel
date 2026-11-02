# Domain WHOIS & Expiry Lookup — VoidOnyX Security Suite (`tools.voidonyx.in`)

A production-ready, full-stack web application designed for real-time domain registration queries, expiry countdown tracking, EPP status flag translation, nameserver inspection, and GDPR privacy compliance checks.

Part of the **VoidOnyX Network & Security Utilities** family (sitting alongside the VoidOnyX SSL/TLS Checker and RBL Checker tools).

---

## Technical Architecture & Flow

```
+------------------+         +-----------------------+         +--------------------------+
| React + Vite UI  | ------> | Express Backend API   | ------> | MongoDB (Cache & Audit)  |
|  (Tailwind CSS)  |         | (lookupService.js)    |         | (whois_cache, lookups)   |
+------------------+         +-----------------------+         +--------------------------+
                                     |           |
               1. Try RDAP HTTPS     |           |  2. Fallback WHOIS TCP Port 43
                                     v           v
                          +------------------+  +-------------------------------+
                          | IANA RDAP Server |  | Registry WHOIS (Verisign/IN)  |
                          | (RFC 7482/9083)  |  | 1-Hop Registrar Referral Follow|
                          +------------------+  +-------------------------------+
```

### 1. Lookup Engine & Authority Resolution
- **IANA Referral Discovery:** The backend dynamically queries `https://data.iana.org/rdap/dns.json` and `whois.iana.org` on port 43 to find the correct authoritative registry endpoints for any top-level domain (TLD), avoiding hardcoded limits while maintaining a seeded cache map in MongoDB (`tld_server_map`).
- **Primary Source (RDAP RFC 7482/9083):** Queries RDAP over HTTPS JSON for modern gTLDs and ccTLDs. RDAP returns structured JSON, making date and entity extraction fast and reliable.
- **Fallback Source (TCP Port 43 WHOIS):** For ccTLDs or legacy registries without RDAP support, the system initiates a raw TCP socket connection on port 43.
- **Registrar Referral Follow:** If a registry response points to a `Registrar WHOIS Server`, the client automatically follows the referral **1-hop maximum** (preventing infinite loops) to retrieve detailed registrar and contact metadata.

### 2. Normalization & Compliance Engine
- **Input Sanitization:** Strips protocols (`http://`, `https://`), path parameters, trailing slashes, port numbers, and `www.` prefixes. Converts internationalized domain names (IDN) to Punycode (`xn--...`).
- **IP Address Rejection:** Rejects IPv4/IPv6 inputs with a clear guidance message directing users to the VoidOnyX IP/RBL tool.
- **EPP Status Flag Translation:** Parses codes like `clientTransferProhibited`, `serverHold`, `clientDeleteProhibited` into plain-English explanations.
- **GDPR Redaction Handling:** Detects `REDACTED FOR PRIVACY` notices without failing the record, labeling it as **Privacy-Protected**.
- **Available Domain Detection:** Detects `NOT FOUND` or `No match for domain` responses and highlights the domain as **Available (Unregistered)**.

### 3. Caching & Rate Limiting
- **`whois_cache`:** Cached lookup records backed by MongoDB TTL indexes (`expiresAt: 1`, `expireAfterSeconds: 0`), auto-purging entries after 30–60 minutes.
- **`rate_limits`:** Sliding-window rate limiter enforcing 10 lookups/minute per IP hash, returning standard HTTP 429 status and reset timers.

---

## Directory Structure

```
.
├── backend/
│   ├── src/
│   │   ├── config/          # MongoDB connection module
│   │   ├── models/          # Mongoose schemas (Lookup, WhoisCache, TldServerMap, RateLimit)
│   │   ├── services/
│   │   │   ├── domainNormalizer.js  # Normalizer & IDN Punycode encoder
│   │   │   ├── ianaBootstrap.js     # IANA bootstrap RDAP & port 43 WHOIS resolver
│   │   │   ├── rdapClient.js        # HTTPS RDAP JSON client (RFC 7482)
│   │   │   ├── whoisClient.js       # Native TCP port 43 WHOIS socket client
│   │   │   ├── statusParser.js      # EPP status flag to plain-English dictionary
│   │   │   └── lookupService.js     # Orchestrator for cache, lookup, and audit logging
│   │   ├── middleware/      # RateLimiter & Central Error Handler
│   │   └── routes/          # Express API endpoints (/api/whois/lookup, /api/whois/history)
│   ├── tests/               # Jest & Supertest integration suite with mongodb-memory-server
│   ├── server.js
│   ├── package.json
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/      # Header, DomainInput, StatusBadge, DaysRemainingCard, ResultsCard, etc.
│   │   ├── index.css        # VoidOnyX dark terminal styling system
│   │   └── App.jsx
│   ├── package.json
│   └── vite.config.js
├── docker-compose.yml
├── README.md
└── TECHNICAL_ARTICLE.md     # Technical article with embedded UI screenshots
```

---

## Getting Started & Local Development

### Option A: Docker Compose (Quickest)

```bash
docker-compose up --build
```
This spins up:
- MongoDB server on `localhost:27017`
- Express API server on `http://localhost:5000`

### Option B: Manual Local Setup

1. **Start Local MongoDB:**
   Ensure MongoDB is running locally on `mongodb://localhost:27017` (or set `MONGODB_URI` in `.env`).

2. **Start Backend Service:**
   ```bash
   cd backend
   npm install
   cp .env.example .env
   npm run dev
   ```
   Backend will start on `http://localhost:5000`.

3. **Start Frontend Service:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   Frontend will start on `http://localhost:3000`.

---

## Environment Variables (`backend/.env`)

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `PORT` | `5000` | Express server port |
| `MONGODB_URI` | `mongodb://localhost:27017/voidonyx_whois` | Connection URI for MongoDB |
| `CACHE_TTL_SECONDS` | `3600` | Duration to cache WHOIS responses (default 1 hour) |
| `RATE_LIMIT_WINDOW_MS` | `60000` | Sliding rate limit window (60 seconds) |
| `RATE_LIMIT_MAX_REQUESTS` | `10` | Max lookups allowed per window per IP |
| `SOCKET_TIMEOUT_MS` | `8000` | Port 43 TCP socket and HTTPS timeout |

---

## Automated Tests

Run the backend unit & integration test suite (using `mongodb-memory-server`):

```bash
cd backend
npm test
```

Tests cover:
- Domain syntax validation, protocol stripping, and IDN Punycode encoding.
- IP address input rejection.
- WHOIS text parsing (including standard Verisign, GDPR redacted, and available domain fixtures).
- Referral WHOIS server extraction.
- End-to-end lookup API endpoints (`POST /api/whois/lookup`, `GET /api/health`).

---

## Future Enhancements

1. **Historical WHOIS Diffing:** Track changes in registrar, nameservers, or registrant org over time by diffing historical entries in `lookups`.
2. **Domain Expiry Webhooks / Email Alerts:** Allow users to register notifications when monitored domains cross the 30-day or 7-day expiration thresholds.
3. **DNS propagation & A/AAAA lookup integration:** Combine WHOIS records with live active DNS record resolution.
