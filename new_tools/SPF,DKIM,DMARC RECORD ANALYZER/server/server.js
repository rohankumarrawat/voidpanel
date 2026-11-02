import express from 'express';
import cors from 'cors';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import dotenv from 'dotenv';
import { connectDB } from './config/db.js';
import apiRoutes from './routes/api.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '..');

dotenv.config({ path: path.join(projectRoot, '.env') });

const app = express();
const port = process.env.PORT || 5000;

// Enable CORS
app.use(cors());

// Body parser
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Serve static assets from public folder
app.use(express.static(path.join(projectRoot, 'public')));

// Mount API routes
app.use('/api', apiRoutes);

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({
    status: 'ok',
    uptime: process.uptime(),
    timestamp: new Date().toISOString(),
  });
});

// Fallback for Single Page Application
app.get('*', (req, res) => {
  res.sendFile(path.join(projectRoot, 'public', 'index.html'));
});

const server = app.listen(port, () => {
  console.log(`[Server] SPF/DKIM/DMARC Record Analyzer running on http://localhost:${port}`);
  connectDB();
});

server.on('error', (err) => {
  if (err.code === 'EADDRINUSE') {
    console.error(`[Server Error] Port ${port} is already in use by another process. Please stop the running process or change PORT in .env.`);
    process.exit(1);
  } else {
    console.error('[Server Error]', err);
  }
});


