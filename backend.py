"""
Queens Park Station Departure Scraper
This script scrapes live departure times from Transperth website.

To use this in production:
1. Install dependencies: pip install flask beautifulsoup4 requests flask-cors
2. Run this script on a server: python backend.py
3. Update the frontend HTML to call this API endpoint instead of simulated data
4. Deploy both frontend and backend together

Example deployment options:
- Heroku (free tier available)
- Railway
- Render
- Your own VPS
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

# Transperth URLs
URLS = {
    'armadale': 'https://www.transperth.wa.gov.au/Timetables/Live-Train-Times?line=Armadale%20Line&station=Queens%20Park%20Stn',
    'thornlie': 'https://www.transperth.wa.gov.au/Timetables/Live-Train-Times?line=Thornlie-Cockburn%20Line&station=Queens%20Park%20Stn'
}

def parse_departure_time(time_str):
    """Convert time string to minutes from now"""
    time_str = time_str.strip().lower()
    
    if 'now' in time_str or 'due' in time_str:
        return 0
    
    # Extract number from string like "5 min" or "5min"
    match = re.search(r'(\d+)', time_str)
    if match:
        return int(match.group(1))
    
    # If it's a time like "10:45", calculate minutes until that time
    time_match = re.search(r'(\d{1,2}):(\d{2})', time_str)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2))
        now = datetime.now()
        departure = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # If time is earlier, assume it's for tomorrow
        if departure < now:
            from datetime import timedelta
            departure += timedelta(days=1)
        
        diff = (departure - now).total_seconds() / 60
        return int(diff)
    
    return None

def scrape_transperth(url, line_name):
    """Scrape departure information from Transperth website"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        departures = []
        
        # Find departure rows (adjust selectors based on actual HTML structure)
        # This is a generic approach - you'll need to inspect the actual HTML
        departure_rows = soup.find_all('tr', class_=re.compile('departure|train|service'))
        
        if not departure_rows:
            # Try alternative selectors
            departure_rows = soup.find_all('div', class_=re.compile('departure|train|service'))
        
        for row in departure_rows:
            try:
                # Extract information (adjust based on actual HTML structure)
                platform = row.find(class_=re.compile('platform|plat'))
                destination = row.find(class_=re.compile('destination|dest'))
                time = row.find(class_=re.compile('time|depart|due'))
                pattern = row.find(class_=re.compile('pattern|type'))
                stops = row.find(class_=re.compile('stops|via'))
                
                if platform and destination and time:
                    platform_text = platform.get_text(strip=True)
                    destination_text = destination.get_text(strip=True)
                    time_text = time.get_text(strip=True)
                    pattern_text = pattern.get_text(strip=True) if pattern else 'W'
                    stops_text = stops.get_text(strip=True) if stops else 'All Stations'
                    
                    minutes = parse_departure_time(time_text)
                    
                    if minutes is not None:
                        departures.append({
                            'platform': platform_text,
                            'destination': destination_text,
                            'time_display': time_text,
                            'minutes': minutes,
                            'pattern': pattern_text,
                            'stops': stops_text,
                            'line': line_name
                        })
            except Exception as e:
                print(f"Error parsing row: {e}")
                continue
        
        return departures
    
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return []
    except Exception as e:
        print(f"Error processing departures: {e}")
        return []

@app.route('/api/departures', methods=['GET'])
def get_departures():
    """API endpoint to get all departures"""
    try:
        # Scrape both lines
        armadale_departures = scrape_transperth(URLS['armadale'], 'Armadale')
        thornlie_departures = scrape_transperth(URLS['thornlie'], 'Thornlie-Cockburn')
        
        # Combine and separate by direction
        all_departures = armadale_departures + thornlie_departures
        
        # Separate Perth-bound vs South-bound
        perth_departures = [
            d for d in all_departures 
            if 'perth' in d['destination'].lower() and 'perth' not in d['destination'].lower().replace('perth', '')
        ]
        
        south_departures = [
            d for d in all_departures 
            if d not in perth_departures
        ]
        
        # Sort by time
        perth_departures.sort(key=lambda x: x['minutes'])
        south_departures.sort(key=lambda x: x['minutes'])
        
        return jsonify({
            'success': True,
            'perth': perth_departures[:10],  # Limit to next 10
            'south': south_departures[:10],
            'last_updated': datetime.now().isoformat()
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/')
def index():
    """Serve a simple info page"""
    return '''
    <html>
        <head><title>Queens Park Station API</title></head>
        <body style="font-family: Arial; padding: 40px; max-width: 600px; margin: 0 auto;">
            <h1>Queens Park Station Departure API</h1>
            <p>This is the backend API for scraping Transperth live departure times.</p>
            <h2>Endpoints:</h2>
            <ul>
                <li><code>GET /api/departures</code> - Get all departures</li>
                <li><code>GET /api/health</code> - Health check</li>
            </ul>
            <h2>Frontend Setup:</h2>
            <p>Update your frontend JavaScript to call:</p>
            <pre style="background: #f0f0f0; padding: 10px; border-radius: 5px;">
const response = await fetch('http://your-backend-url/api/departures');
const data = await response.json();
            </pre>
        </body>
    </html>
    '''

if __name__ == '__main__':
    print("🚆 Queens Park Station Departure API")
    print("=" * 50)
    print("Starting server on http://localhost:5000")
    print("API endpoint: http://localhost:5000/api/departures")
    print("\nNote: This needs to be deployed on a server that can access")
    print("Transperth website. Local development may have network restrictions.")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)
