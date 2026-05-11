"""
VIX Proxy Server
Optimized for Render deployment.
Provides a stable, HTTPS-enabled endpoint for VIX data from Yahoo Finance.
"""

from flask import Flask, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)

# CRITICAL: Enable CORS so that your HTML page can call this API from any domain.
# This is required for the proxy to work when hosted on a separate server.
CORS(app)

# Yahoo Finance VIX endpoint
YF_VIX_URL = 'https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX?interval=1d&range=1d'

# HTTP headers to mimic browser request and avoid being blocked by Yahoo Finance
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Origin': 'https://finance.yahoo.com',
    'Referer': 'https://finance.yahoo.com/quote/%5EVIX'
}

@app.route('/vix', methods=['GET'])
def get_vix():
    """
    Fetches current VIX data from Yahoo Finance.
    Returns JSON with price and percent change.
    """
    try:
        # Fetch from Yahoo Finance
        response = requests.get(
            YF_VIX_URL,
            headers=HEADERS,
            timeout=10
        )

        if response.status_code != 200:
            return jsonify({
                'error': f'Yahoo Finance returned status {response.status_code}',
                'available': False
            }), 502

        data = response.json()

        # Parse VIX data from Yahoo Finance response
        result = data.get('chart', {}).get('result', [None])[0]
        if not result:
            return jsonify({
                'error': 'Invalid response structure from Yahoo Finance',
                'available': False
            }), 502

        meta = result.get('meta', {})
        price = meta.get('regularMarketPrice')
        prev_close = meta.get('chartPreviousClose')

        if price is None:
            return jsonify({
                'error': 'VIX price not found in response',
                'available': False
            }), 502

        # Calculate percent change
        pct_change = None
        if prev_close and prev_close > 0:
            pct_change = round((price - prev_close) / prev_close * 100, 2)

        return jsonify({
            'price': price,
            'previousClose': prev_close,
            'pctChange': pct_change,
            'source': 'Yahoo Finance (via Cloud Proxy)',
            'available': True,
            'timestamp': meta.get('regularMarketTime')
        })

    except requests.Timeout:
        return jsonify({
            'error': 'Request timeout while fetching VIX',
            'available': False
        }), 504
    except requests.RequestException as e:
        return jsonify({
            'error': f'Request failed: {str(e)}',
            'available': False
        }), 502
    except Exception as e:
        return jsonify({
            'error': f'Unexpected error: {str(e)}',
            'available': False
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for the proxy server.
    Render uses this to monitor if the service is running.
    """
    return jsonify({
        'status': 'ok',
        'service': 'VIX Proxy'
    }), 200

@app.route('/', methods=['GET'])
def index():
    """Index route."""
    return jsonify({
        'service': 'VIX Proxy Server',
        'endpoints': {
            '/vix': 'GET - Fetch current VIX data',
            '/health': 'GET - Health check'
        }
    })

if __name__ == '__main__':
    # Render automatically sets the PORT environment variable.
    port = int(os.environ.get('PORT', 5000))

    # Run the server
    # Note: In production on Render, Gunicorn is typically used instead of app.run
    app.run(
        host='0.0.0.0',
        port=port
    )
