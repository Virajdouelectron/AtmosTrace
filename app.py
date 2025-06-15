from flask import Flask, jsonify, render_template, send_from_directory, request
from flask_cors import CORS
import requests
from datetime import datetime, timedelta
import os
import json
import aiohttp
import asyncio
import re

app = Flask(__name__, static_folder='static')
CORS(app)

# API endpoints for different data sources
NASA_API_URL = os.getenv('NASA_API_URL', 'https://ssd-api.jpl.nasa.gov/fireball.api')
METEOR_SOCIETY_API = 'https://www.meteorsociety.org/api/v1/meteors'
AMS_API = 'https://www.amsmeteors.org/api/v1/meteors'
NASA_IMAGE_API = 'https://images-api.nasa.gov/search'
YOUTUBE_API = 'https://www.googleapis.com/youtube/v3/search'
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY', '')  # You'll need to set this in your environment

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
            async with session.get(NASA_IMAGE_API, params={'q': query, 'media_type': 'image'}) as response:
                nasa_data = await response.json()
                if 'collection' in nasa_data and 'items' in nasa_data['collection']:
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
                async with session.get(YOUTUBE_API, params=params) as response:
                    youtube_data = await response.json()
                    if 'items' in youtube_data:
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
            async with session.get(api_url) as response:
                data = await response.json()
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
            async with session.get(METEOR_SOCIETY_API, params=params) as response:
                data = await response.json()
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
            async with session.get(AMS_API, params=params) as response:
                data = await response.json()
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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/meteors')
async def get_meteors():
    time_range = request.args.get('time_range', 'realtime')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if time_range == 'custom' and start_date and end_date:
        start = start_date
        end = end_date
    else:
        end = datetime.utcnow()
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
    
    meteors = await fetch_all_meteor_data(start, end)
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