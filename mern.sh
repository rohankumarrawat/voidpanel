#!/bin/bash

# Usage: mern.sh <project_name> <frontend_build_path> <project_directory> <port>
if [ $# -lt 4 ]; then
  echo "Usage: $0 <project_name> <frontend_build_path> <project_directory> <port>"
  exit 1
fi

PROJECT_NAME=$1
FRONTEND_BUILD_PATH=$2
PROJECT_DIR=$3
PORT_NUM=$4
MONGO_URI="mongodb://localhost:27017/${PROJECT_NAME}_db"

echo "==> Creating project directories..."
mkdir -p "$PROJECT_DIR"/{backend,frontend}
cd "$PROJECT_DIR"

# ── Backend ─────────────────────────────────────────────────────────────────
echo "==> Setting up backend..."

cat > "$PROJECT_DIR/backend/index.js" << 'JSEOF'
const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
require('dotenv').config();

const app = express();
app.use(cors());
app.use(express.json());

mongoose
    .connect(process.env.MONGO_URI, { useNewUrlParser: true, useUnifiedTopology: true })
    .then(() => console.log('MongoDB Connected'))
    .catch((err) => console.error(err));

app.get('/api', (req, res) => res.send('API is running...'));

const port = parseInt(process.env.PORT, 10) || 3001;
app.listen(port, '127.0.0.1', () => {
    console.log('Server running at http://127.0.0.1:' + port);
});
JSEOF

cat > "$PROJECT_DIR/backend/package.json" << 'PKGEOF'
{
  "name": "backend",
  "version": "1.0.0",
  "main": "index.js",
  "scripts": { "start": "node index.js" },
  "dependencies": {
    "express": "^4.18.2",
    "mongoose": "^7.6.3",
    "dotenv": "^16.3.1",
    "cors": "^2.8.5"
  }
}
PKGEOF

# Write .env so process.env.PORT resolves correctly even without PM2
cat > "$PROJECT_DIR/backend/.env" << ENVEOF
PORT=${PORT_NUM}
MONGO_URI=${MONGO_URI}
ENVEOF

echo "==> Installing backend dependencies..."
cd "$PROJECT_DIR/backend"
npm install
cd "$PROJECT_DIR"

# ── Frontend ─────────────────────────────────────────────────────────────────
echo "==> Creating React app..."
npx -y create-react-app frontend

echo "==> Patching React proxy to backend port ${PORT_NUM}..."
node -e "
const fs = require('fs');
const p = '$PROJECT_DIR/frontend/package.json';
const pkg = JSON.parse(fs.readFileSync(p, 'utf8'));
pkg.proxy = 'http://127.0.0.1:${PORT_NUM}';
fs.writeFileSync(p, JSON.stringify(pkg, null, 2));
console.log('proxy patched');
"

echo "==> Building React frontend (production)..."
cd "$PROJECT_DIR/frontend"
npm install
npm run build
cd "$PROJECT_DIR"

echo "==> Copying build to Nginx directory..."
mkdir -p "$FRONTEND_BUILD_PATH"
cp -r "$PROJECT_DIR/frontend/build"/* "$FRONTEND_BUILD_PATH/"

# ── PM2 ──────────────────────────────────────────────────────────────────────
echo "==> Deploying backend with PM2..."

cat > "$PROJECT_DIR/backend/ecosystem.config.js" << ECOEOF
module.exports = {
  apps: [{
    name: "${PROJECT_NAME}",
    script: "index.js",
    cwd: "${PROJECT_DIR}/backend",
    env: {
      NODE_ENV: "production",
      MONGO_URI: "${MONGO_URI}",
      PORT: ${PORT_NUM}
    }
  }]
};
ECOEOF

# Stop any prior instance to avoid EADDRINUSE port conflict
pm2 delete "${PROJECT_NAME}" 2>/dev/null || true

cd "$PROJECT_DIR/backend"
pm2 start ecosystem.config.js
pm2 save
cd "$PROJECT_DIR"

echo "==> Done. '${PROJECT_NAME}' backend is live on 127.0.0.1:${PORT_NUM}"
