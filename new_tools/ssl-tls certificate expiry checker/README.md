# VoidOnyX — SSL/TLS Certificate & Expiry Checker

> Part of the **VoidOnyX** suite of network and security utilities (`tools.voidonyx.in/ssl-checker`).

![VoidOnyX SSL/TLS Checker UI](https://raw.githubusercontent.com/voidonyx/ssl-checker/main/docs/preview.png)

## Overview

The **SSL/TLS Certificate & Expiry Checker** is a full-stack, production-grade cybersecurity tool designed to inspect live TLS/SSL certificates on any domain or IP address.

Unlike generic tools that rely on third-party REST APIs, VoidOnyX opens a **native raw TLS socket handshake** directly against the target server, pulling live peer certificates, verifying Subject Alternative Names (SANs), measuring chain depth, calculating remaining validity days, and probing TLS 1.2 & 1.3 protocol compatibility.

---

## Technical Stack

- **Frontend:** React 18, Vite, Tailwind CSS, Lucide Icons, JetBrains Mono font system.
- **Backend:** Node.js (Express), Native `tls` & `crypto` modules.
- **Database Layer:** MongoDB (Mongoose ODM) with native **TTL (Time-To-Live) indexes** for automatic cache eviction and distributed rate limiting.
- **Testing:** Jest, Supertest, `mongodb-memory-server` for isolated test runs.
- **Deployment:** Docker & Docker Compose setup.

---

## Directory Structure

```
├── backend/
│   ├── Dockerfile
│   ├── package.json
│   ├── src/
│   │   ├── app.js               # Express application bootstrap
│   │   ├── server.js            # Node server listener & DB connection
│   │   ├── config/              # Environment variable configurations
│   │   ├── db/
│   │   │   ├── connection.js    # Mongoose connection with exponential retry
│   │   │   └── models/          # Lookup, CertCache, RateLimit Mongoose schemas
│   │   ├── routes/              # Express API endpoints (/api/check, /api/recent, /api/health)
│   │   ├── services/            # Raw TLS socket checker, cache engine, rate limiter
│   │   └── utils/               # Cert parser, SAN wildcard matcher, IP hasher
│   └── tests/                   # Jest unit & integration tests with memory server
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   ├── index.html
│   └── src/
│       ├── App.jsx              # Main React state container & layout
│       ├── components/          # Header, SearchForm, StatusBanner, CertDetails, etc.
│       └── utils/               # API fetch layer
├── db/
│   ├── schemas/                 # JSON schema specifications for MongoDB collections
│   └── seed.js                  # CLI seeding script for test lookups & TTL index creation
├── docker-compose.yml           # Multi-container orchestration (Mongo 6 + API + Client)
├── .env.example                 # Environment configuration template
└── README.md                    # Project documentation
```

---

## Core Architecture & Key Features

### 1. Native Node.js TLS Socket Handshake
The engine invokes `tls.connect()` with explicit SNI (`servername`) configuration:
- Sets an explicit timeout (default **8 seconds**) to capture connection hangs cleanly.
- Configures `rejectUnauthorized: false` to extract complete certificate details even when encountering self-signed, expired, or untrusted root chains, flagging them appropriately rather than failing outright.
- Calls `socket.getPeerCertificate(true)` to extract the leaf certificate and recursively traverse parent issuer certificates.
- Performs a secondary socket handshake forcing `minVersion: 'TLSv1.2', maxVersion: 'TLSv1.2'` to test backward protocol compatibility.

### 2. MongoDB TTL Indexes & Rate-Limiting
- **`cert_cache` Collection:** Caches complete parsed results per `host:port` using a MongoDB TTL index on `expiresAt` (`{ expireAfterSeconds: 0 }`). Repeat lookups within 10 minutes return instantly without re-running handshakes.
- **`rate_limits` Collection:** Enforces 10 requests/minute per client IP hash. Uses a MongoDB TTL index to auto-delete expired window counters. Survives server restarts and scales horizontally across multiple container instances.
- **`lookups` Collection:** Log audit trail storing hostname, port, certificate status, days remaining, cryptographic key type, and SHA-256 IP hash for telemetry.

### 3. Privacy-First IP Anonymization
Client IP addresses are salted and hashed using **SHA-256** prior to rate limiting or database logging. Raw IP addresses are never written to disk or logs.

---

## Quick Start & Local Setup

### Prerequisites
- Node.js >= 18.0.0
- Docker & Docker Compose (optional, for containerized run)
- MongoDB instance (local or MongoDB Atlas free tier)

### Option A: Local Development (npm)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/voidonyx/ssl-checker.git
   cd ssl-checker
   ```

2. **Backend Setup:**
   ```bash
   cd backend
   npm install
   cp ../.env.example .env
   ```

3. **Database Seeding & TTL Index Setup:**
   ```bash
   node ../db/seed.js
   ```

4. **Start Backend Server:**
   ```bash
   npm run dev
   # Runs on http://localhost:5000
   ```

5. **Frontend Setup (in a new terminal):**
   ```bash
   cd frontend
   npm install
   npm run dev
   # Runs on http://localhost:3000
   ```

---

### Option B: Docker Compose

Spin up the entire application stack (MongoDB container + Backend API + React Frontend) with a single command:

```bash
docker-compose up --build
```
Access the application at `http://localhost:3000`.

---

## Automated Testing

Run unit and integration tests using `mongodb-memory-server` (requires no external MongoDB server):

```bash
cd backend
npm test
```

### Tested Scenarios:
- ✅ Certificate parsing logic (valid cert, expiring cert, self-signed cert, expired cert).
- ✅ SAN matching and wildcard domain checking (`*.domain.com`).
- ✅ Domain, IPv4, IPv6, and shorthand `host:port` validation.
- ✅ Cache hit/miss functionality via MongoDB TTL.
- ✅ Rate-limiting headers and 429 status code returns.

---

## Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `PORT` | `5000` | Port for Express backend API |
| `MONGODB_URI` | `mongodb://localhost:27017/ssl_checker` | MongoDB connection URI |
| `CACHE_TTL_SECONDS` | `600` | Certificate cache TTL duration in seconds (10 mins) |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Rolling rate limit window duration in seconds |
| `RATE_LIMIT_MAX_REQUESTS` | `10` | Maximum lookups per IP hash per window |
| `TLS_TIMEOUT_MS` | `8000` | Handshake timeout duration in milliseconds |

---

## Future Roadmap & Enhancements

1. **OCSP Stapling & Revocation Checks:** Check Online Certificate Status Protocol (OCSP) responses and Certificate Revocation Lists (CRLs) to detect revoked certificates in real-time.
2. **CAA Record Inspection:** Perform DNS queries to verify Certification Authority Authorization (CAA) DNS records.
3. **Webhook & Email Expiry Alerts:** Allow users to register domain monitors that trigger webhook/Slack/email alerts 30, 14, and 7 days prior to certificate expiration.
