# VoidOnyx Tools Platform

Free developer & server admin tools by VoidOnyx — powered by VoidPanel.

## Live URL
- **Frontend**: `https://tools.voidonyx.in`
- **API**: `https://tools.voidonyx.in/api`

## Architecture

```
tools-platform/
├── client/          ← React + Vite + Tailwind frontend
├── server/          ← Express + TypeScript + MongoDB backend
├── nginx.conf       ← Nginx vhost config for tools.voidonyx.in
└── ecosystem.config.js  ← PM2 production config
```

## Deployment Steps

### 1. Upload to server
```bash
# Copy the tools-platform directory to your server
scp -r tools-platform/ root@your-server:/home/voidonyx/tools-platform/
```

### 2. Install & Build Backend
```bash
cd /home/voidonyx/tools-platform/server
cp .env.example .env
# Edit .env with your MongoDB URI and production settings
npm install
npm run build
```

### 3. Install & Build Frontend
```bash
cd /home/voidonyx/tools-platform/client
npm install
npm run build
# Copy built files to the public_html directory
cp -r dist/* /public_html/tools/
```

### 4. Start with PM2
```bash
cd /home/voidonyx/tools-platform
pm2 delete voidtools 2>/dev/null || true
pm2 start ecosystem.config.js
pm2 save
```

### 5. Configure Nginx
```bash
# Copy nginx.conf to your Nginx sites directory
# (VoidPanel may have already configured this for the subdomain)
cp nginx.conf /etc/nginx/conf.d/tools.voidonyx.in.conf
nginx -t && systemctl reload nginx
```

## Adding New Tools

1. Add an entry to `server/src/routes/registry.ts` in the `TOOLS_REGISTRY` array
2. Create a new folder in `client/src/tools/[tool-slug]/`
3. Create the tool page component (e.g. `WhoisPage.tsx`)
4. Add the route in `client/src/App.tsx`
5. If the tool needs a backend API, create the route in `server/src/routes/`

## Current Tools

| Tool | Status | Category |
|------|--------|----------|
| DNS Record Checker | ✅ Live | DNS & Domain |
| WHOIS Lookup | 🔜 Coming Soon | DNS & Domain |
| IP Geolocation | 🔜 Coming Soon | Networking |
| SSL Certificate Checker | 🔜 Coming Soon | SSL & Security |
| MX Record Lookup | 🔜 Coming Soon | Email |
| SPF Record Validator | 🔜 Coming Soon | Email |
| HTTP Header Inspector | 🔜 Coming Soon | SSL & Security |
| UTM Link Builder | 🔜 Coming Soon | Marketing |
