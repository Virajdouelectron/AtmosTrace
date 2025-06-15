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

# API endpoints for different data sources
NASA_API_URL = os.getenv('NASA_API_URL', 'https://ssd-api.jpl.nasa.gov/fireball.api')
METEOR_SOCIETY_API = 'https://data.amsmeteors.org/api/v1/meteors'
AMS_API = 'https://data.amsmeteors.org/api/v1/meteors'
NASA_IMAGE_API = 'https://images-api.nasa.gov/search'
YOUTUBE_API = 'https://www.googleapis.com/youtube/v3/search'
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY', 'AIzaSyB2Io9clw4XQjqjLH29kGt0B2SpPctVy90')

# Add a timeout for all API requests
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
                timeout=REQUEST_TIMEOUT,
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
            nasa_data = await fetch_with_retry(session, NASA_IMAGE_API, params={'q': query, 'media_type': 'image'})
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
        if YOUTUBE_API_KEY:
            search_query = f"meteor {meteor_data['time_utc']} {meteor_data['type']}"
            params = {
                'part': 'snippet',
                'q': search_query,
                'type': 'video',
                'maxResults': 3,
                'key': YOUTUBE_API_KEY
            }
            async with aiohttp.ClientSession() as session:
                youtube_data = await fetch_with_retry(session, YOUTUBE_API, params=params)
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

async def fetch_nasa_data(start_date, end_date):
    try:
        api_url = f"{NASA_API_URL}?date-min={start_date}&date-max={end_date}&limit=100"
        async with aiohttp.ClientSession() as session:
            data = await fetch_with_retry(session, api_url)
            return data.get('data', [])
    except Exception as e:
        print(f"Error fetching NASA data: {e}")
        return []

async def fetch_meteor_society_data(start_date, end_date):
    try:
        params = {
            'start_date': start_date,
            'end_date': end_date,
            'limit': 100
        }
        async with aiohttp.ClientSession() as session:
            data = await fetch_with_retry(session, METEOR_SOCIETY_API, params=params)
            return data.get('meteors', [])
    except Exception as e:
        print(f"Error fetching Meteor Society data: {e}")
        return []

async def fetch_ams_data(start_date, end_date):
    try:
        params = {
            'start_date': start_date,
            'end_date': end_date,
            'limit': 100
        }
        async with aiohttp.ClientSession() as session:
            data = await fetch_with_retry(session, AMS_API, params=params)
            return data.get('meteors', [])
    except Exception as e:
        print(f"Error fetching AMS data: {e}")
        return []

def process_meteor_data(raw_data, source):
    meteors = []
    for entry in raw_data:
        try:
            if source == 'nasa':
                date_str, energy, impact_e, lat, lon, alt, vel = entry
                magnitude = (float(energy) / 1000) ** 0.5 if energy else 0
            elif source == 'meteor_society':
                magnitude = float(entry.get('magnitude', 0))
                lat = float(entry.get('latitude', 0))
                lon = float(entry.get('longitude', 0))
                vel = float(entry.get('velocity', 0))
                date_str = entry.get('date')
            else:  # ams
                magnitude = float(entry.get('magnitude', 0))
                lat = float(entry.get('latitude', 0))
                lon = float(entry.get('longitude', 0))
                vel = float(entry.get('velocity', 0))
                date_str = entry.get('date')

            if magnitude < 2.5:
                continue

            meteor = {
                'id': f"meteor_{len(meteors)}",
                'time_utc': date_str,
                'lat': lat,
                'lng': lon,
                'magnitude': round(magnitude, 2),
                'velocity_kms': round(vel, 2),
                'type': 'High-Energy Fireball' if magnitude >= 6 else 'Fireball',
                'source': source,
                'mapLink': f"https://www.google.com/maps?q={lat},{lon}"
            }
            
            meteors.append(meteor)
        except Exception as e:
            print(f"Error processing meteor entry: {e}")
            continue
    
    return meteors

async def fetch_all_meteor_data(start_date, end_date):
    # Fetch data from all sources concurrently
    nasa_data, meteor_society_data, ams_data = await asyncio.gather(
        fetch_nasa_data(start_date, end_date),
        fetch_meteor_society_data(start_date, end_date),
        fetch_ams_data(start_date, end_date)
    )
    
    # Process data from each source
    all_meteors = []
    all_meteors.extend(process_meteor_data(nasa_data, 'nasa'))
    all_meteors.extend(process_meteor_data(meteor_society_data, 'meteor_society'))
    all_meteors.extend(process_meteor_data(ams_data, 'ams'))
    
    # Sort by date
    all_meteors.sort(key=lambda x: x['time_utc'], reverse=True)
    
    # Fetch media data for each meteor
    for meteor in all_meteors:
        meteor['media'] = await fetch_meteor_media(meteor)
    
    return all_meteors

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