#!/usr/bin/env node
/**
 * Webhook-based Token Refresh Service (Node.js)
 * Simple and clean - uses youtube-po-token-generator
 */

const express = require('express');
const { generate } = require('youtube-po-token-generator');
const axios = require('axios');

const app = express();
app.use(express.json());

// Serve static files from public directory
const path = require('path');
app.use(express.static(path.join(__dirname, 'public')));

// Configuration from environment variables
const LAVALINK_URL = process.env.LAVALINK_URL || 'http://194.58.66.44:7087';
const LAVALINK_PASSWORD = process.env.LAVALINK_PASSWORD || 'glace';
const PORT = process.env.PORT || 8000;

// Ensure URL has protocol
const lavalinkUrl = LAVALINK_URL.startsWith('http://') || LAVALINK_URL.startsWith('https://') 
    ? LAVALINK_URL 
    : `http://${LAVALINK_URL}`;

console.log('='.repeat(60));
console.log('YouTube Token Refresh Webhook Service');
console.log('='.repeat(60));
console.log(`Lavalink URL: ${lavalinkUrl}`);
console.log(`Port: ${PORT}`);
console.log('='.repeat(60));

/**
 * Generate new token using youtube-po-token-generator
 */
async function generateToken() {
    try {
        console.log('Generating new token...');
        const result = await generate();
        console.log('✅ Token generated successfully');
        return result;
    } catch (error) {
        console.error('❌ Error generating token:', error.message);
        throw error;
    }
}

/**
 * Update Lavalink token via REST API
 */
async function updateLavalinkToken(token, visitorData) {
    try {
        // Ensure no double slashes in URL
        const baseUrl = lavalinkUrl.replace(/\/+$/, ''); // Remove trailing slashes
        const url = `${baseUrl}/youtube`;
        const headers = {
            'Content-Type': 'application/json',
            'Authorization': LAVALINK_PASSWORD
        };
        const payload = {
            poToken: token,
            visitorData: visitorData
        };

        console.log(`Updating Lavalink token at ${url}...`);
        console.log(`Token length: ${token.length}, VisitorData length: ${visitorData.length}`);
        
        const response = await axios.post(url, payload, { headers, timeout: 10000 });

        if (response.status === 204) {
            console.log('✅ Successfully updated Lavalink token!');
            console.log(`   poToken: ${token.substring(0, 20)}...`);
            console.log(`   visitorData: ${visitorData.substring(0, 20)}...`);
            return true;
        } else {
            console.error(`❌ Failed to update token. Status: ${response.status}`);
            return false;
        }
    } catch (error) {
        console.error('❌ Error updating Lavalink token:', error.message);
        if (error.response) {
            console.error(`   Status: ${error.response.status}`);
            console.error(`   Response: ${JSON.stringify(error.response.data)}`);
        }
        return false;
    }
}

/**
 * Refresh token endpoint
 */
app.get('/refresh', async (req, res) => {
    try {
        console.log('Token refresh requested via webhook');
        
        const tokens = await generateToken();
        
        if (!tokens || !tokens.poToken || !tokens.visitorData) {
            return res.status(500).json({
                success: false,
                error: 'Failed to generate token'
            });
        }

        const updated = await updateLavalinkToken(tokens.poToken, tokens.visitorData);
        
        if (updated) {
            return res.json({
                success: true,
                message: 'Token refreshed successfully'
            });
        } else {
            return res.status(500).json({
                success: false,
                error: 'Failed to update Lavalink'
            });
        }
    } catch (error) {
        console.error('Error in refresh endpoint:', error);
        return res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

app.post('/refresh', async (req, res) => {
    // Same handler logic as GET
    try {
        console.log('Token refresh requested via webhook');
        
        const tokens = await generateToken();
        
        if (!tokens || !tokens.poToken || !tokens.visitorData) {
            return res.status(500).json({
                success: false,
                error: 'Failed to generate token'
            });
        }

        const updated = await updateLavalinkToken(tokens.poToken, tokens.visitorData);
        
        if (updated) {
            return res.json({
                success: true,
                message: 'Token refreshed successfully'
            });
        } else {
            return res.status(500).json({
                success: false,
                error: 'Failed to update Lavalink'
            });
        }
    } catch (error) {
        console.error('Error in refresh endpoint:', error);
        return res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * Health check endpoint
 */
app.get('/health', (req, res) => {
    res.json({ status: 'healthy' });
});

/**
 * Serve static HTML UI
 */
app.get('/', (req, res) => {
    // Check if request wants HTML
    if (req.headers.accept && req.headers.accept.includes('text/html')) {
        res.sendFile('public/index.html', { root: __dirname });
    } else {
        // JSON API response
        res.json({
            service: 'Lavalink Token Refresh Webhook',
            endpoints: {
                '/refresh': 'POST or GET - Refresh YouTube token',
                '/health': 'GET - Health check'
            },
            lavalink_url: lavalinkUrl
        });
    }
});

// Start server
app.listen(PORT, '0.0.0.0', () => {
    console.log('');
    console.log('✅ Webhook server started!');
    console.log('');
    console.log('Endpoints:');
    console.log(`  GET/POST http://localhost:${PORT}/refresh - Refresh token`);
    console.log(`  GET http://localhost:${PORT}/health - Health check`);
    console.log('');
});

