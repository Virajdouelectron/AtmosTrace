from flask import Flask, jsonify, render_template, send_from_directory
from flask_cors import CORS
import requests
from datetime import datetime
import os

app = Flask(__name__, static_folder='static')
CORS(app)

# Use environment variable for API URL
NASA_API_URL = os.getenv('NASA_API_URL', 'https://ssd-api.jpl.nasa.gov/fireball.api?limit=20')

def fetch_meteor_data():
    try:
        # Fetch data from NASA's Fireball API
        response = requests.get(NASA_API_URL)
        data = response.json()
        
        if 'data' not in data:
            print("No data found in API response")
            return []
            
        meteors = []
        for entry in data['data']:
            try:
                # Parse the data according to NASA CNEOS Fireball API format
                # Format: date, energy, impact-e, lat, lon, alt, vel
                date_str, energy, impact_e, lat, lon, alt, vel = entry
                
                # Convert to float and handle missing values
                try:
                    energy = float(energy) if energy else 0
                    lat = float(lat) if lat else 0
                    lon = float(lon) if lon else 0
                    vel = float(vel) if vel else 0
                except (ValueError, TypeError):
                    continue
                
                # Calculate magnitude based on energy (kt)
                magnitude = (energy / 1000) ** 0.5  # Simplified magnitude calculation
                
                # Skip if magnitude is too low
                if magnitude < 2.5:
                    continue
                
                meteor = {
                    'id': f"meteor_{len(meteors)}",
                    'time_utc': date_str,
                    'lat': lat,
                    'lng': lon,
                    'magnitude': round(magnitude, 2),
                    'velocity_kms': round(vel, 2),
                    'type': 'High-Energy Fireball' if energy > 100 else 'Fireball',
                    'energy': round(energy, 2),
                    'impact_energy': round(float(impact_e) if impact_e else 0, 2),
                    'altitude': round(float(alt) if alt else 0, 2),
                    'velocity': round(vel, 2),
                    'utc_time': date_str,
                    'mapLink': f"https://www.google.com/maps?q={lat},{lon}"
                }
                
                meteors.append(meteor)
            except Exception as e:
                print(f"Error processing meteor entry: {e}")
                continue
                
        return meteors
    except Exception as e:
        print(f"Error fetching meteor data: {e}")
        return []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/meteors')
def get_meteors():
    meteors = fetch_meteor_data()
    return jsonify(meteors)

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    # Use environment variable for port, default to 8080
    port = int(os.getenv('PORT', 8080))
    # In production, don't use debug mode
    debug = os.getenv('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug) 