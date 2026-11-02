# ⚡ HTTP Header & Redirect Tracer

> A full-stack web tool and API engine to trace HTTP redirect chains (301, 302, 307, 308), measure multi-hop response latency, and automatically audit modern security headers (`HSTS`, `CSP`, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`).

![HTTP Redirect Tracer Screenshot](https://raw.githubusercontent.com/placeholder/tracer.png)

---

## 🌟 Key Features

- **Iterative Redirect Tracing**: Sequentially follows HTTP redirects up to **10 hops** maximum.
- **Detailed Hop Metrics**: Reports exact status codes (`301 Moved Permanently`, `302 Found`, `307 Temporary`, `308 Permanent`, `200 OK`), resolution latency in milliseconds, protocol (`HTTP` vs `HTTPS`), and the `Location` redirect header.
- **Security Headers Audit**: Scans response headers against DevSecOps best practices for:
  - `Strict-Transport-Security` (HSTS)
  - `Content-Security-Policy` (CSP)
  - `X-Frame-Options` (Clickjacking Protection)
  - `X-Content-Type-Options` (MIME-Sniffing Guard)
  - `Referrer-Policy` (Information Leakage Control)
  - `Permissions-Policy` (Browser Feature Access)
- **Security Scoring & Remediation**: Generates letter grades (A+ to F), severity flags (PASS, WARNING, FAIL), plain-language risk explanations, and copyable server configuration snippets (**Nginx**, **Apache**, **Express**).
- **Loop & Latency Detection**: Automatically identifies redirect loops (e.g. `A -> B -> A`) and multi-hop performance bottlenecks.
- **Enterprise-Grade SSRF Protection**: Restricts requests to internal/private IP ranges (`127.0.0.1`, `10.0.0.0/8`, `192.168.0.0/16`, `172.16.0.0/12`, link-local, loopback).
- **Backend Rate Limiting**: Built-in IP rate limiter preventing service abuse.

---

## 🛠️ Architecture & Tech Stack

- **Backend**: Node.js, Express, Rate Limiter, `ipaddr.js` for IP range parsing, Jest & Supertest.
- **Frontend**: React 18, Vite, Lucide Icons, Glassmorphism Tailwind CSS styling framework.

```
/
├── package.json          # Root scripts to orchestrate client & server
├── README.md             # Project documentation
├── ARTICLE.md            # Technical Article (1,000+ words) with SEO Metadata
├── TEAM_LEAD_REVIEW_SUMMARY.md  # Sign-off summary for SEO Lead
├── server/
│   ├── server.js         # Express app entry point
│   ├── routes/trace.js   # POST /api/trace API route
│   ├── services/
│   │   ├── redirectTracer.js          # Hop execution & SSRF protection
│   │   └── securityHeaderAnalyzer.js  # Security audit rules engine
│   └── tests/
│       └── tracer.test.js             # Automated Jest test suite
└── client/
    ├── src/              # React components & UI layout
    └── vite.config.js    # Vite configuration & API proxying
```

---

## 🚀 Quick Start Guide

### Prerequisites
- Node.js `v18.0.0` or higher
- npm `v9.0.0` or higher

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/http-header-redirect-tracer.git
   cd http-header-redirect-tracer
   ```

2. Install dependencies:
   ```bash
   # Install server dependencies
   npm --prefix server install

   # Install client dependencies
   npm --prefix client install
   ```

### Running Locally

To run the server and client concurrently in development mode:

```bash
# Run server (port 3001) & client (port 3000)
npm run dev
```

Open your browser and navigate to:
```
http://localhost:3000
```

### Running Production Build

To build the frontend and serve it directly via Express:

```bash
# Build frontend static files
npm --prefix client run build

# Start production server on port 3001
npm run start
```
Navigate to `http://localhost:3001`.

---

## 🧪 Running Automated Tests

The test suite validates SSRF blocking rules, header evaluation logic, loop detection, and endpoint edge cases:

```bash
npm test
```

### Test Coverage Summary:
- ✅ SSRF loopback (`127.0.0.1`, `localhost`) & private range blocking (`10.x`, `192.168.x`).
- ✅ Public domain resolution permission.
- ✅ Security scoring calculation (A+ vs F).
- ✅ Validation of missing HSTS & CSP flags.
- ✅ API 400 error responses for empty or restricted inputs.

---

## 📡 API Reference

### `POST /api/trace`

Inspects a target domain or URL and returns the complete redirect timeline and security audit.

#### Request Body
```json
{
  "url": "http://google.com"
}
```

#### Response Example (200 OK)
```json
{
  "success": true,
  "data": {
    "inputUrl": "http://google.com",
    "finalUrl": "https://www.google.com/",
    "totalHops": 2,
    "totalTimeMs": 184,
    "loopDetected": false,
    "maxHopsExceeded": false,
    "chain": [
      {
        "hop": 1,
        "url": "http://google.com",
        "statusCode": 301,
        "statusText": "Moved Permanently",
        "location": "http://www.google.com/",
        "responseTimeMs": 42,
        "protocol": "HTTP",
        "headers": {
          "location": "http://www.google.com/",
          "content-type": "text/html; charset=UTF-8"
        }
      },
      {
        "hop": 2,
        "url": "http://www.google.com/",
        "statusCode": 200,
        "statusText": "OK",
        "location": null,
        "responseTimeMs": 142,
        "protocol": "HTTPS",
        "headers": {
          "content-type": "text/html; charset=ISO-8859-1"
        }
      }
    ],
    "securityAudit": {
      "score": 0,
      "grade": "F",
      "audits": [
        {
          "header": "Strict-Transport-Security",
          "status": "FAIL",
          "summary": "Missing HSTS Header",
          "recommendation": "Add Strict-Transport-Security with max-age=31536000."
        }
      ]
    }
  }
}
```

---

## 📜 License

MIT License © 2026 HTTP Header & Redirect Tracer Team
