require('dotenv').config();
const app = require('./src/app');
const { connectDB } = require('./src/config/db');

const PORT = process.env.PORT || 5000;

async function startServer() {
  // Connect to MongoDB
  await connectDB();

  app.listen(PORT, () => {
    console.log(`[VoidOnyX WHOIS API] Server running on port ${PORT} (http://localhost:${PORT})`);
  });
}

startServer();
