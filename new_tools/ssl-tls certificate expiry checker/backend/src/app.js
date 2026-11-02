const express = require('express');
const cors = require('cors');
const healthRoutes = require('./routes/health');
const sslRoutes = require('./routes/ssl');

const app = express();

app.use(cors());
app.use(express.json());

// Routes
app.use('/api', healthRoutes);
app.use('/api', sslRoutes);

// 404 Handler
app.use((req, res) => {
  res.status(404).json({
    error: 'Not Found',
    message: `Endpoint ${req.method} ${req.originalUrl} does not exist.`,
  });
});

// Global Error Handler
app.use((err, req, res, next) => {
  console.error('[Global Express Error]', err);
  res.status(500).json({
    error: 'Internal Server Error',
    message: 'An unexpected server error occurred.',
  });
});

module.exports = app;
