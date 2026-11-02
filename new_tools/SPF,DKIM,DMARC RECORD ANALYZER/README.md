# SPF, DKIM & DMARC Record Analyzer (TOOL-05)

A production-ready MERN web tool for real-time analysis, validation, and auditing of domain email authentication postures (SPF, DKIM, and DMARC DNS records).

---

## 📐 Architecture Diagram

```
                              ┌────────────────────────┐
                              │  React 18 SPA (Client) │
                              │ (Tailwind / Modern CSS)│
                              └───────────┬────────────┘
                                          │
                                HTTP POST │ GET
                                          ▼
                              ┌────────────────────────┐
                              │  Express Server (Node) │
                              │  (Rate Limiter, CORS)  │
                              └───────────┬────────────┘
                                          │
             ┌────────────────────────────┼───────────────────────────┐
             │                            │                           │
             ▼                            ▼                           ▼
  ┌──────────────────┐          ┌──────────────────┐        ┌───────────────────┐
  │  domainValidator │          │   dnsAnalyzer    │        │  MongoDB / Memory │
  │ (Punycode/ASCII) │          │ (dns.promises)   │        │ (scans Collection)│
  └──────────────────┘          └─────────┬────────┘        └───────────────────┘
                                          │
                        ┌─────────────────┴─────────────────┐
                        │ DNS TXT Queries (8.8.8.8/1.1.1.1) │
                        ▼                                   ▼
               Root & _dmarc Records               <selector>._domainkey
```

### Architecture Description
1. **Frontend**: Single-Page Application (SPA) built with React 18 and modern CSS styling. Features live domain validation, responsive score cards, recursive SPF lookup tree viewer, and audit log history.
2. **Backend**: Express.js server utilizing Node's asynchronous DNS module (`node:dns/promises`) with custom 5-second explicit timeout handling to avoid hanging queries.
3. **Validation & Analysis Engine**:
   - **SPF Engine**: Parses mechanisms and qualifiers (`+`, `-`, `~`, `?`), handles nested `include:` / `redirect=` recursion, builds lookup trees, and enforces the RFC 7208 10-DNS-lookup limit.
   - **DKIM Engine**: Queries custom and common selectors (`google`, `selector1`, `s1`, `default`, etc.), inspects public key `p=` tags, verifies Base64 formatting, and flags revoked keys.
   - **DMARC Engine**: Evaluates `p=`, `sp=`, `pct=`, `rua=`, `ruf=`, alignment modes (`adkim`, `aspf`), and flags un-enforced monitoring policies (`p=none`).
4. **Data Layer**: MongoDB `scans` collection via Mongoose, with an in-memory fallback mechanism if MongoDB is temporarily unavailable.
5. **Security & Protection**: Input sanitization preventing DNS injection, IDNA/Punycode normalization, and IP-based rate limiting via `express-rate-limit`.

---

## 🛠️ Setup Instructions

### Prerequisites
- Node.js (v18+)
- npm (v9+)
- MongoDB (Optional, for persistent scan log storage)

### Installation
1. Clone the repository and navigate into the root directory:
   ```bash
   cd "SPF,DKIM,DMARC RECORD ANALYZER"
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Create environment file `.env`:
   ```env
   PORT=3000
   MONGO_URI=mongodb://127.0.0.1:27017/spf_dkim_dmarc_db
   RATE_LIMIT_WINDOW_MS=60000
   RATE_LIMIT_MAX=30
   ```

4. Start the application:
   - Development mode with auto-reload:
     ```bash
     npm run dev
     ```
   - Production mode:
     ```bash
     npm start
     ```
   Open `http://localhost:3000` in your web browser.

5. Run automated unit test suite:
   ```bash
   npm test
   ```

---

## 🔌 API Documentation

### `POST /api/analyze`
Executes full SPF, DKIM, and DMARC DNS resolution for a domain.

**Request Body:**
```json
{
  "domain": "example.com",
  "selectors": ["google", "s1", "custom_selector"]
}
```

**Response Body:**
```json
{
  "domain": "example.com",
  "spf": {
    "found": true,
    "valid": true,
    "record": "v=spf1 include:_spf.google.com ~all",
    "lookupCount": 1,
    "maxLookupsExceeded": false,
    "terminalQualifier": "~all",
    "issues": [],
    "lookupTree": [...]
  },
  "dkim": {
    "selectorsChecked": ["google", "s1"],
    "foundCount": 1,
    "results": [
      {
        "selector": "google",
        "fqdn": "google._domainkey.example.com",
        "found": true,
        "valid": true,
        "record": "v=DKIM1; k=rsa; p=MIIBIjANBg...",
        "keyType": "rsa",
        "revoked": false,
        "issues": []
      }
    ]
  },
  "dmarc": {
    "found": true,
    "valid": true,
    "record": "v=DMARC1; p=reject; rua=mailto:dmarc@example.com",
    "policy": "reject",
    "subdomainPolicy": "reject",
    "pct": 100,
    "rua": ["mailto:dmarc@example.com"],
    "ruf": [],
    "alignment": { "spf": "relaxed", "dkim": "relaxed" },
    "issues": []
  },
  "overallScore": "Good",
  "timestamp": "2026-08-15T12:00:00.000Z"
}
```

### `GET /api/history?domain=example.com`
Retrieves past domain analysis logs.

### `GET /api/default-selectors`
Returns list of common DKIM selectors checked by default.

---

## 📦 Pull Request Summary

### Features Built
- ⚡ **DNS Inspection Engine**: Async non-blocking lookup engine using Node's `dns.promises.Resolver`.
- 🔍 **SPF Lookup Counter**: Recursive tree solver tracking mechanisms (`include`, `redirect`, `a`, `mx`, `ptr`, `exists`) to strictly validate RFC 7208 10-lookup limits.
- 🔑 **DKIM Public Key Validator**: Key type parser, Base64 sanity checker, and empty `p=` revocation flag detector.
- 🛡️ **DMARC & Alignment Parser**: Alignment mode parser (`adkim`, `aspf`), reporting target extraction (`rua`, `ruf`), and `p=none` enforcement warnings.
- 🎨 **Modern React UI**: Interactive score badge, dark mode glassmorphism UI, copy buttons, and audit trail table.
- 📊 **Persistence & Resilience**: MongoDB audit logging with in-memory fallback and rate limiting middleware.

### Known Limitations
1. **DKIM Selector Discovery**: DNS does not support wildcards or listing records inside standard zone files without DNSSEC zone walking. DKIM selector discovery is inherently best-guess based on common defaults (`google`, `selector1`, `s1`, `default`, `k1`, `mail`) or user-supplied custom selectors.
2. **Dynamic SPF IP Macro Expansion**: SPF macro expansion (e.g. `%{i}`) is analyzed statically without resolving client-ip-dependent macros.
