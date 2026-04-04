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

// Ensure Express listens on the Unix socket (use path to prevent errors)
const socketPath = '/var/run/$PROJECT_NAME.sock';
app.listen(socketPath, () => {
    console.log(`Server running at ${socketPath}`);
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
      },
      args: "--unix-socket /var/run/$PROJECT_NAME.sock"
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

sudo chown www-data:www-data /var/run/$PROJECT_NAME.sock
sudo chmod 777 /var/run/$PROJECT_NAME.sock



<?php

if (!defined("WHMCS")) {
    die("This file cannot be accessed directly.");
}

function voidpanel_MetaData() {
    return [
        'DisplayName' => 'VoidPanel',
        'APIVersion' => '1.0',
        'RequiresServer' => true
    ];
}

function voidpanel_ConfigOptions() {
    return [
        'package' => [
            'FriendlyName' => 'Package Name',
            'Type' => 'text',
            'Size' => '25',
            'Default' => 'default_package',
            'Description' => 'Enter the package name in VoidPanel'
        ],
        'Secure Connection' => [
            'FriendlyName' => 'Secure Connection',
            'Type' => 'yesno',
            'Description' => 'Tick this box for a secure (HTTPS) connection.'
        ]
    ];
}

function voidpanel_getBaseUrl($params) {
    $secure = (isset($params['configoption2']) && $params['configoption2'] === 'on');
    $protocol = $secure ? 'https' : 'http';
    $port = $secure ? 8082 : 8080;
    $host = rtrim($params['serverhostname'], '/');
    return $protocol . '://' . $host . ':' . $port;
}

function voidpanel_Authenticate($params) {
    $baseUrl = voidpanel_getBaseUrl($params);
    $apiUrl = $baseUrl . '/api/auth/';
    $username = $params['serverusername'];
    $password = $params['serverpassword'];

    $response = voidpanel_sendRequest($apiUrl, [
        'username' => $username,
        'password' => $password
    ]);

    logModuleCall('voidpanel', 'Authenticate', ['apiUrl' => $apiUrl, 'username' => $username], $response);

    return (isset($response['status']) && $response['status'] === 'success') ? $response['session_token'] : false;
}

function voidpanel_CreateAccount($params) {
    $sessionToken = voidpanel_Authenticate($params);
    if (!$sessionToken) {
        return ['success' => false, 'message' => 'Authentication failed.'];
    }

    $baseUrl = voidpanel_getBaseUrl($params);
    $apiUrl = $baseUrl . '/api/create-account/';
    $data = [
        'session_token' => $sessionToken,
        'domain' => $params['domain'],
        'username' => $params['username'],
        'password' => $params['password'],
        'package' => $params['configoption1'],
        'client_id' => $params['clientsdetails']['userid']
    ];

   $response = voidpanel_sendRequest($apiUrl, $data);
    logModuleCall('voidpanel', 'CreateAccount', $data, $response);

    if (isset($response['status']) && $response['status'] === 'success') {
        return 'success';
    } else {
        return 'Error: ' . ($response['message'] ?? 'Unknown error');
    }
        
}

function voidpanel_SuspendAccount($params) {
    return voidpanel_Action($params, '/api/suspend-account/', 'SuspendAccount');
}

function voidpanel_UnsuspendAccount($params) {
    return voidpanel_Action($params, '/api/unsuspend-account/', 'UnsuspendAccount');
}

function voidpanel_TerminateAccount($params) {
    return voidpanel_Action($params, '/api/terminate-account/', 'TerminateAccount');
}

function voidpanel_Action($params, $endpoint, $action) {
    $sessionToken = voidpanel_Authenticate($params);
    if (!$sessionToken) {
        return ['success' => false, 'message' => 'Authentication failed.'];
    }

    $baseUrl = voidpanel_getBaseUrl($params);
    $apiUrl = $baseUrl . $endpoint;
    $data = ['session_token' => $sessionToken, 'username' => $params['username']];

    $response = voidpanel_sendRequest($apiUrl, $data);
    logModuleCall('voidpanel', $action, $data, $response);

    return (isset($response['status']) && $response['status'] === 'success')
        ? ['success' => true, 'message' => ucfirst($action) . ' successful.']
        : ['success' => false, 'message' => 'Error: ' . ($response['message'] ?? 'Unknown error')];
}

function voidpanel_FetchPackages($params) {
    $sessionToken = voidpanel_Authenticate($params);
    if (!$sessionToken) return ['success' => false, 'message' => 'Authentication failed.'];

    $baseUrl = voidpanel_getBaseUrl($params);
    $apiUrl = $baseUrl . '/api/list-packages/';
    $response = voidpanel_sendRequest($apiUrl, ['session_token' => $sessionToken]);

    return isset($response['packages']) ? $response['packages'] : [];
}

function voidpanel_AutoLogin($params) {
    $sessionToken = voidpanel_Authenticate($params);
    if (!$sessionToken) return ['success' => false, 'message' => 'Authentication failed.'];

    $secure = (isset($params['configoption2']) && $params['configoption2'] === 'on');
    $protocol = $secure ? 'https' : 'http';
    $host = rtrim($params['serverhostname'], '/');
    return ['success' => true, 'redirect' => $protocol . '://' . $host . '/dashboard'];
}

function voidpanel_AdminCustomButtonArray() {
    return ["Verify Connection" => "testConnection"];
}

function voidpanel_testConnection($params) {
    $sessionToken = voidpanel_Authenticate($params);
    logModuleCall('voidpanel', 'Test Connection', $params, $sessionToken);

    return $sessionToken
        ? ['success' => true, 'message' => "✅ Successfully connected to VoidPanel!"]
        : ['success' => false, 'message' => "❌ Connection failed. Check credentials and API URL."];
}

function voidpanel_sendRequest($url, $data) {
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
    curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, true);

    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $error = curl_error($ch);
    curl_close($ch);

    if ($error) {
        return ['status' => 'error', 'message' => 'cURL Error: ' . $error];
    }

    $decoded = json_decode($response, true);
    return $decoded ?: ['status' => 'error', 'message' => 'Invalid JSON. HTTP Code: ' . $httpCode];
}

?>