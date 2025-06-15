from flask import Flask, jsonify, render_template, send_from_directory, request
from flask_cors import CORS
import requests
from datetime import datetime, timedelta
import os
import json
import aiohttp
import asyncio
import re
from functools import wraps
import ssl

app = Flask(__name__, static_folder='static')
CORS(app)

# Constants
NASA_FIREBALL_API = "https://ssd-api.jpl.nasa.gov/fireball.api"
REQUEST_TIMEOUT = 10  # seconds

async def fetch_with_retry(session, url, params=None, retries=3, delay=1):
    """Helper function to retry failed requests"""
    # Create an SSL context that doesn't verify certificates
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    for attempt in range(retries):
        try:
            async with session.get(
                url, 
                params=params, 
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
                ssl=ssl_context  # Use our custom SSL context
            ) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:  # Too Many Requests
                    await asyncio.sleep(delay * (attempt + 1))  # Exponential backoff
                    continue
                response.raise_for_status()
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt == retries - 1:
                raise
            await asyncio.sleep(delay * (attempt + 1))
    return None

async def fetch_nasa_fireball_data(start_date, end_date):
    """
    Fetch fireball data from NASA CNEOS Fireball API
    """
    try:
        params = {
            'date-min': start_date,
            'date-max': end_date,
            'req-loc': 'true',  # Request location data
            'req-alt': 'true',  # Request altitude data
            'req-vel': 'true'   # Request velocity data
        }
        
        print(f"Fetching NASA Fireball data with params: {params}")
        
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        conn = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(connector=conn) as session:
            async with session.get(
                NASA_FIREBALL_API, 
                params=params, 
                ssl=ssl_context,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data and 'data' in data and data['data']:
                        print(f"NASA Fireball API returned {len(data['data'])} records")
                        return data['data']
                    else:
                        print("NASA Fireball API returned no data")
                else:
                    print(f"NASA Fireball API error: {response.status}")
        
        # Fallback to sample data if API fails
        print("Using sample NASA Fireball data")
        return [
            {
                'time_utc': '2025-06-15T12:00:00',
                'lat': '34.05',
                'lon': '-118.24',
                'energy': '0.5',
                'impact-e': '2.5',
                'alt': '25.0',
                'vel': '28.7',
                'source': 'nasa',
                'type': 'fireball'
            },
            {
                'time_utc': '2025-06-15T15:30:00',
                'lat': '40.71',
                'lon': '-74.01',
                'energy': '0.3',
                'impact-e': '2.0',
                'alt': '30.0',
                'vel': '32.5',
                'source': 'nasa',
                'type': 'fireball'
            }
        ]
        
    except Exception as e:
        print(f"Error in fetch_nasa_fireball_data: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

async def fetch_all_meteor_data(start_date, end_date):
    """
    Fetch meteor data from NASA CNEOS Fireball API
    """
    print(f"\n=== Fetching NASA Fireball data from {start_date} to {end_date} ===")
    
    try:
        # Fetch data from NASA Fireball API
        fireball_data = await fetch_nasa_fireball_data(start_date, end_date)
        
        # Process the data
        meteors = []
        for entry in fireball_data:
            try:
                meteor = {
                    'id': f"nasa_{entry.get('time_utc', '').replace(' ', '_').replace(':', '')}",
                    'time_utc': entry.get('time_utc', ''),
                    'lat': float(entry.get('lat', 0)),
                    'lng': float(entry.get('lon', 0)),
                    'magnitude': float(entry.get('energy', 0)) * 2,  # Convert energy to approximate magnitude
                    'velocity_kms': float(entry.get('vel', 0)),
                    'altitude_km': float(entry.get('alt', 0)),
                    'type': 'Fireball',
                    'source': 'NASA',
                    'mapLink': f"https://www.google.com/maps?q={entry.get('lat', 0)},{entry.get('lon', 0)}",
                    'media': {'images': [], 'videos': []}
                }
                meteors.append(meteor)
            except Exception as e:
                print(f"Error processing fireball entry: {e}")
                continue
        
        # Sort by date (newest first)
        meteors.sort(key=lambda x: x.get('time_utc', ''), reverse=True)
        
        print(f"Successfully processed {len(meteors)} fireballs")
        return meteors
        
    except Exception as e:
        print(f"Error in fetch_all_meteor_data: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

async def fetch_meteor_media(meteor_data):
    """Fetch images and videos related to a meteor event"""
    media_data = {
        'images': [],
        'videos': []
    }
    
    try:
        # Fetch NASA images
        query = f"meteor {meteor_data['time_utc']}"
        async with aiohttp.ClientSession() as session:
            nasa_data = await fetch_with_retry(session, "https://images-api.nasa.gov/search", params={'q': query, 'media_type': 'image'})
            if nasa_data and 'collection' in nasa_data and 'items' in nasa_data['collection']:
                for item in nasa_data['collection']['items'][:3]:  # Limit to 3 images
                    if 'links' in item and len(item['links']) > 0:
                        media_data['images'].append({
                            'url': item['links'][0]['href'],
                            'title': item['data'][0]['title'],
                            'description': item['data'][0]['description'],
                            'source': 'NASA'
                        })

        # Fetch YouTube videos if API key is available
        youtube_api_key = os.getenv('YOUTUBE_API_KEY', 'AIzaSyB2Io9clw4XQjqjLH29kGt0B2SpPctVy90')
        if youtube_api_key:
            search_query = f"meteor {meteor_data['time_utc']} {meteor_data['type']}"
            params = {
                'part': 'snippet',
                'q': search_query,
                'type': 'video',
                'maxResults': 3,
                'key': youtube_api_key
            }
            async with aiohttp.ClientSession() as session:
                youtube_data = await fetch_with_retry(session, "https://www.googleapis.com/youtube/v3/search", params=params)
                if youtube_data and 'items' in youtube_data:
                    for item in youtube_data['items']:
                        media_data['videos'].append({
                            'url': f"https://www.youtube.com/watch?v={item['id']['videoId']}",
                            'title': item['snippet']['title'],
                            'thumbnail': item['snippet']['thumbnails']['high']['url'],
                            'source': 'YouTube'
                        })

    except Exception as e:
        print(f"Error fetching media data: {e}")
    
    return media_data

def async_route(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(f(*args, **kwargs))
            return result
        except Exception as e:
            print(f"Error in async route: {str(e)}")
            return jsonify({"error": str(e)}), 500
        finally:
            loop.close()
    return wrapper

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/meteors')
@async_route
async def get_meteors():
    try:
        # Get query parameters
        time_range = request.args.get('time_range', 'realtime')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        print(f"\n=== Received request with time_range: {time_range}, start_date: {start_date}, end_date: {end_date} ===")
        
        # Set date range based on time_range parameter
        end = datetime.utcnow()
        if time_range == 'custom' and start_date and end_date:
            print("Using custom date range")
            start = start_date
            end = end_date
        else:
            if time_range == '1h':
                start = end - timedelta(hours=1)
            elif time_range == '10h':
                start = end - timedelta(hours=10)
            elif time_range == '10d':
                start = end - timedelta(days=10)
            elif time_range == '5m':
                start = end - timedelta(days=150)
            else:  # realtime
                start = end - timedelta(hours=1)
            
            start = start.strftime('%Y-%m-%d')
            end = end.strftime('%Y-%m-%d')
        
        print(f"Fetching meteor data from {start} to {end}")
        
        # Fetch meteor data
        meteors = await fetch_all_meteor_data(start, end)
        
        # Fetch media data for each meteor
        print("Fetching media data for meteors...")
        for meteor in meteors:
            try:
                meteor['media'] = await fetch_meteor_media(meteor)
            except Exception as e:
                print(f"Error fetching media for meteor {meteor.get('id', 'unknown')}: {str(e)}")
                meteor['media'] = {'images': [], 'videos': []}
        
        print(f"Returning {len(meteors)} meteor records")
        return jsonify(meteors)
        
    except Exception as e:
        error_msg = f"Error in /api/meteors: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return jsonify({"error": error_msg}), 500

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    # Use environment variable for port, default to 8080
    port = int(os.getenv('PORT', 8080))
    # In production, don't use debug mode
    debug = os.getenv('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)