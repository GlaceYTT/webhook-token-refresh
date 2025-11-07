#!/usr/bin/env python3
"""
Webhook-based Token Refresh Service
For Java-only hosts (Optiklink, Wispbyte) where you can't run Docker Compose
This runs as a separate service that can be called via webhook/cron
"""

import os
import sys
import json
import subprocess
import requests
import logging
import glob
from flask import Flask, request, jsonify
from threading import Thread
import time

app = Flask(__name__)

# Configuration
LAVALINK_URL = os.getenv("LAVALINK_URL", "http://localhost:9296")
# Ensure URL has protocol
if LAVALINK_URL and not LAVALINK_URL.startswith(("http://", "https://")):
    LAVALINK_URL = f"http://{LAVALINK_URL}"
LAVALINK_PASSWORD = os.getenv("LAVALINK_PASSWORD", "glace")
USE_DOCKER = os.getenv("USE_DOCKER", "true").lower() == "true"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_token_python():
    """Generate token using Python (works on Render without Docker)"""
    try:
        logger.info("Generating new token using Python method...")
        
        # Try to use the generator script directly
        generator_path = "/app/generator/main.py"
        if not os.path.exists(generator_path):
            generator_path = "/app/generator/generate.py"
        if not os.path.exists(generator_path):
            # Try to find any Python file in generator directory
            import glob
            py_files = glob.glob("/app/generator/*.py")
            if py_files:
                generator_path = py_files[0]
            else:
                logger.error("Generator script not found")
                return None
        
        # Run the generator with headless environment
        env = os.environ.copy()
        env['DISPLAY'] = ':99'  # Virtual display
        env['HEADLESS'] = 'true'
        
        # Start Xvfb in background if not running
        subprocess.Popen(['Xvfb', ':99', '-screen', '0', '1024x768x24'], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL)
        time.sleep(1)  # Give Xvfb time to start
        
        # Run the generator
        result = subprocess.run(
            ["python3", generator_path],
            cwd="/app/generator",
            capture_output=True,
            text=True,
            timeout=120,
            env=env
        )
        
        output = result.stdout + result.stderr
        
        # Parse output
        token = None
        visitor_data = None
        
        # Try JSON parsing
        try:
            json_start = output.find('{')
            json_end = output.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(output[json_start:json_end])
                token = data.get('token') or data.get('poToken')
                visitor_data = data.get('visitorData') or data.get('visitor_data')
        except:
            pass
        
        # Fallback: line-by-line parsing
        if not token or not visitor_data:
            for line in output.split('\n'):
                line_lower = line.lower()
                if 'token' in line_lower and ':' in line and len(line.split(':')) > 1:
                    potential_token = line.split(':', 1)[1].strip().strip('"').strip("'")
                    if len(potential_token) > 20:  # Tokens are usually long
                        token = potential_token
                elif ('visitor' in line_lower and 'data' in line_lower) or 'visitordata' in line_lower:
                    if ':' in line:
                        visitor_data = line.split(':', 1)[1].strip().strip('"').strip("'")
        
        if token and visitor_data:
            logger.info("Successfully generated new token using Python")
            return {"token": token, "visitorData": visitor_data}
        else:
            logger.error(f"Failed to parse token from output. Output: {output[:500]}")
            return None
            
    except subprocess.TimeoutExpired:
        logger.error("Token generation timed out")
        return None
    except Exception as e:
        logger.error(f"Error generating token with Python: {e}")
        return None


def generate_token_docker():
    """Generate token using Docker container (fallback if Docker available)"""
    try:
        logger.info("Generating new token using Docker...")
        result = subprocess.run(
            ["docker", "run", "--rm", "iv-org/youtube-trusted-session-generator"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            logger.error(f"Docker command failed: {result.stderr}")
            return None
        
        output = result.stdout
        
        # Parse output
        token = None
        visitor_data = None
        
        # Try JSON parsing
        try:
            json_start = output.find('{')
            json_end = output.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(output[json_start:json_end])
                token = data.get('token') or data.get('poToken')
                visitor_data = data.get('visitorData') or data.get('visitor_data')
        except:
            pass
        
        # Fallback: line-by-line parsing
        if not token or not visitor_data:
            for line in output.split('\n'):
                if 'token' in line.lower() and ':' in line:
                    token = line.split(':', 1)[1].strip().strip('"').strip("'")
                elif 'visitor' in line.lower() and 'data' in line.lower() and ':' in line:
                    visitor_data = line.split(':', 1)[1].strip().strip('"').strip("'")
        
        if token and visitor_data:
            logger.info("Successfully generated new token")
            return {"token": token, "visitorData": visitor_data}
        else:
            logger.error("Failed to parse token from output")
            return None
            
    except FileNotFoundError:
        logger.info("Docker not available, trying Python method...")
        return generate_token_python()
    except Exception as e:
        logger.error(f"Error generating token: {e}")
        return generate_token_python()  # Fallback to Python


def update_lavalink_token(token, visitor_data):
    """Update Lavalink token via REST API"""
    try:
        url = f"{LAVALINK_URL}/youtube"
        headers = {
            "Content-Type": "application/json",
            "Authorization": LAVALINK_PASSWORD
        }
        payload = {
            "poToken": token,
            "visitorData": visitor_data
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 204:
            logger.info("✅ Successfully updated Lavalink token!")
            return True
        else:
            logger.error(f"Failed to update token. Status: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error updating Lavalink token: {e}")
        return False


@app.route('/refresh', methods=['POST', 'GET'])
def refresh_token():
    """Webhook endpoint to refresh token"""
    try:
        logger.info("Token refresh requested via webhook")
        
        # Try Python method first (works on Render), fallback to Docker if available
        tokens = generate_token_python()
        if not tokens and USE_DOCKER:
            logger.info("Python method failed, trying Docker...")
            tokens = generate_token_docker()
        
        if not tokens:
            return jsonify({"success": False, "error": "Failed to generate token"}), 500
        
        if update_lavalink_token(tokens["token"], tokens["visitorData"]):
            return jsonify({"success": True, "message": "Token refreshed successfully"}), 200
        else:
            return jsonify({"success": False, "error": "Failed to update Lavalink"}), 500
            
    except Exception as e:
        logger.error(f"Error in refresh endpoint: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200


@app.route('/', methods=['GET'])
def index():
    """Info endpoint"""
    return jsonify({
        "service": "Lavalink Token Refresh Webhook",
        "endpoints": {
            "/refresh": "POST or GET - Refresh YouTube token",
            "/health": "GET - Health check"
        },
        "lavalink_url": LAVALINK_URL
    }), 200


if __name__ == '__main__':
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting webhook server on port {port}")
    logger.info(f"Lavalink URL: {LAVALINK_URL}")
    logger.info("Endpoints:")
    logger.info("  POST/GET /refresh - Refresh token")
    logger.info("  GET /health - Health check")
    app.run(host='0.0.0.0', port=port, debug=False)

