const express = require('express');
const cors = require('cors');
const path = require('path');
const rateLimit = require('express-rate-limit');
const traceRouter = require('./routes/trace');
const historyRouter = require('./routes/history');
const statsRouter = require('./routes/stats');
const { initDatabase } = require('./db/database');
const { connectMongoDB } = require('./db/mongo');

const app = express();
const PORT = process.env.PORT || 3001;

// Initialize persistent database storage & MongoDB Compass connection
initDatabase();
connectMongoDB();

// CORS setup
app.use(cors());

// Rate Limiting (60 requests per 15 mins)
const apiLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 60,
  standardHeaders: true,
  legacyHeaders: false,
  message: {
    success: false,
    error: 'Too many requests from this IP. Please try again after 15 minutes.'
  }
});

app.use(express.json({ limit: '100kb' }));

// Mount API routes with rate limiting
app.use('/api', apiLimiter, traceRouter);
app.use('/api/history', apiLimiter, historyRouter);
app.use('/api/stats', apiLimiter, statsRouter);

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({
    status: 'ok',
    database: 'connected',
    mongodb: 'voidonyx_tracer / scans',
    timestamp: new Date().toISOString()
  });
});

// Serve frontend build static files in production if dist exists
const clientDistPath = path.join(__dirname, '../client/dist');
app.use(express.static(clientDistPath));

app.get('*', (req, res) => {
  if (req.path.startsWith('/api')) {
    return res.status(404).json({ success: false, error: 'API endpoint not found' });
  }
  res.sendFile(path.join(clientDistPath, 'index.html'), (err) => {
    if (err) {
      res.status(404).send('VoidOnyx HTTP Header & Redirect Tracer Backend Server is running.');
    }
  });
});

if (require.main === module) {
  app.listen(PORT, () => {
    console.log(`🚀 VoidOnyx Backend Server listening on http://localhost:${PORT}`);
    console.log(`🍃 MongoDB Compass Connection URI: mongodb://127.0.0.1:27017/voidonyx_tracer`);
  });
}

module.exports = app;
