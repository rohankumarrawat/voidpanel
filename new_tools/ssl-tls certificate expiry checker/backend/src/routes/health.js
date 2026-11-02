const express = require('express');
const mongoose = require('mongoose');

const router = express.Router();

router.get('/health', (req, res) => {
  const dbState = mongoose.connection.readyState;
  const states = ['disconnected', 'connected', 'connecting', 'disconnecting'];

  res.json({
    status: 'ok',
    service: 'voidonyx-ssl-checker-api',
    uptime: process.uptime(),
    timestamp: new Date().toISOString(),
    database: states[dbState] || 'unknown',
  });
});

module.exports = router;
