#!/bin/bash

# Check if sufficient arguments are provided
if [ $# -lt 3 ]; then
  echo "Usage: $0 <project_name> <frontend_build_path> <project_directory>"
  exit 1
fi

# Variables
PROJECT_NAME=$1
MONGO_URI="mongodb://localhost:27017/${PROJECT_NAME}_db"
FRONTEND_BUILD_PATH=$2
PROJECT_DIR=$3

# Create project directories
echo "Creating project directories..."
mkdir -p "$PROJECT_DIR"/{backend,frontend}

# Navigate to the project directory
cd "$PROJECT_DIR"

# Backend Setup
echo "Setting up backend..."

# Create server.js file for Express
cat <<EOF > "$PROJECT_DIR"/backend/server.js
const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
require('dotenv').config();

const app = express();
app.use(cors());
app.use(express.json());

mongoose
    .connect(process.env.MONGO_URI, { useNewUrlParser: true, useUnifiedTopology: true })
    .then(() => console.log("MongoDB Connected"))
    .catch((err) => console.error(err));

app.get('/api', (req, res) => res.send('API is running...'));

module.exports = app;
EOF

# Create index.js file to start Express server
cat <<EOF > "$PROJECT_DIR"/backend/index.js
const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const path = require('path');  // For path handling
require('dotenv').config();

const app = express();
app.use(cors());
app.use(express.json());

mongoose
    .connect(process.env.MONGO_URI, { useNewUrlParser: true, useUnifiedTopology: true })
    .then(() => console.log("MongoDB Connected"))
    .catch((err) => console.error(err));

app.get('/api', (req, res) => res.send('API is running...'));

// Ensure Express listens on the provided environment port
const port = process.env.PORT || 5000;
app.listen(port, '127.0.0.1', () => {
    console.log(`Server running at http://127.0.0.1:${port}`);
});

EOF

# Create package.json file for backend
cat <<EOF > "$PROJECT_DIR"/backend/package.json
{
  "name": "backend",
  "version": "1.0.0",
  "main": "index.js",
  "scripts": {
    "start": "node index.js"
  },
  "dependencies": {
    "express": "^4.17.1",
    "mongoose": "^5.13.8",
    "dotenv": "^10.0.0",
    "cors": "^2.8.5"
  }
}
EOF

# Install backend dependencies
echo "Installing backend dependencies..."
cd "$PROJECT_DIR"/backend
npm install
cd ..

# Frontend Setup (React)
echo "Setting up frontend..."

# Create React app
npx create-react-app frontend

# Add proxy to React app package.json to connect frontend to backend
echo "Configuring proxy in React app..."
jq '. + { "proxy": "/api" }' frontend/package.json > "$PROJECT_DIR"/frontend/package.temp.json
mv "$PROJECT_DIR"/frontend/package.temp.json "$PROJECT_DIR"/frontend/package.json

# Build React app
echo "Building React frontend..."
cd "$PROJECT_DIR"/frontend
npm install
npm run build
cd ..

# Move build files to Nginx directory
echo "Copying frontend build files to Nginx directory..."
sudo mkdir -p "$FRONTEND_BUILD_PATH"
sudo cp -r "$PROJECT_DIR"/frontend/build/* "$FRONTEND_BUILD_PATH/"



# Deploy Backend with PM2
echo "Deploying backend with PM2..."

# Create PM2 ecosystem config file
cat <<EOF > "$PROJECT_DIR"/backend/ecosystem.config.js
module.exports = {
  apps: [
    {
      name: "$PROJECT_NAME",
      script: "index.js",
      env: {
        NODE_ENV: "production",
        MONGO_URI: "mongodb://localhost:27017/${PROJECT_NAME}_db",
        PORT: $4
      }
    }
  ]
};

EOF

# Start backend with PM2 and enable it on startup
cd "$PROJECT_DIR"/frontend
npm install web-vitals
npm run build
cd "$PROJECT_DIR"/backend
pm2 start ecosystem.config.js
pm2 save
pm2 startup
cd ..

