const express = require('express');
const cors = require('cors');
const whoisRoutes = require('./routes/whoisRoutes');
const errorHandler = require('./middleware/errorHandler');

const app = express();

app.use(cors({ origin: '*' }));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Mount API routes
app.use('/api', whoisRoutes);

// Root fallback
app.get('/', (req, res) => {
  res.json({
    name: 'VoidOnyX Domain WHOIS & Expiry Lookup API',
    endpoint: '/api/whois/lookup',
    docs: 'https://tools.voidonyx.in/whois-checker',
  });
});

// Mount error handler
app.use(errorHandler);

module.exports = app;
