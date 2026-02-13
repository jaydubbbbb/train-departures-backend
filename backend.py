"""
Queens Park Station Departure Scraper - FINAL VERSION
Calls Transperth's official API directly - FREE and RELIABLE!
"""

from flask import Flask, jsonify
from flask_cors import CORS
import requests
from datetime import datetime
import re

app = Flask(__name__)
CORS(app)

# Transperth's official API endpoint
API_URL = "https://www.transperth.wa.gov.au/API/SilverRailRestService/SilverRailService/GetStopTimetable"

# Queens Park Station stop codes
STOP_CODES = {
    'platform_1': '99091',  # Platform 1 (Perth-bound)
    'platform_2': '99092'   # Platform 2 (South-bound)
}

def calculate_minutes_until(depart_time_str):
    """Calculate minutes until departure from ISO format time"""
    try:
        depart_time = datetime.fromisoformat(depart_time_str)
        now = datetime.now()
        diff = (depart_time - now).total_seconds() / 60
        return max(0, int(diff))
    except:
        return None

def fetch_departures_for_platform(stop_code):
    """Fetch departures from Transperth API for a specific platform"""
    try:
        # API expects POST with JSON body
        payload = {
            'stopUid': f'PerthRestricted:{stop_code}',
            'maxResults': 20
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Referer': 'https://www.transperth.wa.gov.au/'
        }
        
        print(f"Fetching from API for stop {stop_code}...")
        response = requests.post(API_URL, json=payload, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"API returned status {response.status_code}")
            return []
        
        data = response.json()
        
        if data.get('result') != 'success':
            print(f"API result not success: {data.get('result')}")
            return []
        
        trips = data.get('trips', [])
        print(f"Found {len(trips)} trips for stop {stop_code}")
        
        departures = []
        
        for trip in trips:
            try:
                # Extract platform number from stop name
                stop_name = trip.get('StopTimetableStop', {}).get('Name', '')
                platform_match = re.search(r'Platform\s+(\d+)', stop_name)
                platform = platform_match.group(1) if platform_match else '?'
                
                # Get destination
                summary = trip.get('Summary', {})
                headsign = summary.get('Headsign', '')
                
                # Get display info
                display_title = trip.get('DisplayTripTitle', '')
                display_description = trip.get('DisplayTripDescription', '')
                display_status = trip.get('DisplayTripStatus', '')
                countdown = trip.get('DisplayTripStatusCountDown', '')
                
                # Get route info
                route_name = summary.get('RouteName', '')
                display_route_code = trip.get('DisplayRouteCode', '')
                
                # Get real-time info
                real_time = trip.get('RealTimeInfo', {})
                series = summary.get('RealTimeInfo', {}).get('Series', 'W')
                num_cars = summary.get('RealTimeInfo', {}).get('NumCars', '')
                
                # Calculate minutes
                depart_time = trip.get('DepartTime', '')
                minutes = calculate_minutes_until(depart_time)
                
                if minutes is None:
                    continue
                
                # Build stops description
                stops = f"All Stations"
                if num_cars:
                    stops = f"{stops} ({num_cars} cars)"
                if series:
                    stops = f"{stops} - {series} series"
                
                departures.append({
                    'platform': platform,
                    'destination': display_title or headsign,
                    'time_display': countdown or display_status,
                    'minutes': minutes,
                    'pattern': series or 'W',
                    'stops': stops,
                    'route': route_name,
                    'route_code': display_route_code
                })
                
                print(f"  ✓ {display_title or headsign} in {minutes} min from platform {platform}")
                
            except Exception as e:
                print(f"Error parsing trip: {e}")
                continue
        
        return departures
        
    except Exception as e:
        print(f"Error fetching from API: {e}")
        return []

@app.route('/api/departures', methods=['GET'])
def get_departures():
    """Get all departures for Queens Park Station"""
    try:
        print("=" * 50)
        print("Fetching departures from Transperth API...")
        
        # Fetch from both platforms
        platform_1_deps = fetch_departures_for_platform(STOP_CODES['platform_1'])
        platform_2_deps = fetch_departures_for_platform(STOP_CODES['platform_2'])
        
        all_deps = platform_1_deps + platform_2_deps
        print(f"\nTotal departures: {len(all_deps)}")
        
        # Separate by direction
        # Platform 1 is Perth-bound, Platform 2 is South-bound (Cockburn/Byford)
        perth = [d for d in all_deps if d['platform'] == '1']
        south = [d for d in all_deps if d['platform'] == '2']
        
        perth.sort(key=lambda x: x['minutes'])
        south.sort(key=lambda x: x['minutes'])
        
        return jsonify({
            'success': True,
            'perth': perth[:10],
            'south': south[:10],
            'last_updated': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"Error in get_departures: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/')
def index():
    """Info page"""
    return '''
    <html>
        <head><title>Queens Park Station API</title></head>
        <body style="font-family: Arial; padding: 40px; max-width: 600px; margin: 0 auto;">
            <h1>🚆 Queens Park Station API</h1>
            <p><strong>Status:</strong> Running (using Transperth's official API)</p>
            <p><strong>Free:</strong> No API keys or external services needed!</p>
            <h2>Endpoints:</h2>
            <ul>
                <li><a href="/api/health">/api/health</a> - Health check</li>
                <li><a href="/api/departures">/api/departures</a> - Get live departures</li>
            </ul>
        </body>
    </html>
    '''

if __name__ == '__main__':
    print("🚆 Queens Park Station API - FREE VERSION")
    print("=" * 50)
    print("Using Transperth's official API - completely free!")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)
