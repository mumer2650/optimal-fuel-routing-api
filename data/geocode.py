import csv
import time
import requests
import os
import logging

# Set up logging to console
logging.basicConfig(level=logging.INFO, format='%(message)s')

# Configuration
INPUT_FILE = 'fuel-prices-for-be-assessment.csv'
OUTPUT_FILE = 'fuel-prices-geocoded.csv'
NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search'
USER_AGENT = 'SpotterAssessmentApp/1.0'

def get_coordinates(name, address, city, state):
    url = "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates"
    
    # ArcGIS is smart enough to handle the entire string at once
    # We clean the '#' out of the name just to be safe
    clean_name = name.split('#')[0].strip()
    
    query = f"{clean_name}, {address}, {city}, {state}"
    
    params = {
        "SingleLine": query,
        "f": "json",
        "maxLocations": 1
    }
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get('candidates'):
            loc = data['candidates'][0]['location']
            return loc['y'], loc['x'] # y is lat, x is lng
    except Exception:
        pass
    
    # Fallback: Just Name, City, State
    fallback_query = f"{clean_name}, {city}, {state}"
    params["SingleLine"] = fallback_query
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get('candidates'):
            loc = data['candidates'][0]['location']
            return loc['y'], loc['x']
    except Exception:
        pass

    return None, None

def main():
    # Fault Tolerance: Check where we left off if the script crashed
    processed_count = 0
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            processed_count = sum(1 for _ in f) - 1  # Subtract 1 for the header
            if processed_count < 0:
                processed_count = 0
                
    if processed_count > 0:
        logging.info(f"Resuming from row {processed_count + 1}...")

    # Read all rows into memory to count total
    with open(INPUT_FILE, 'r', encoding='utf-8-sig') as infile:
        reader = list(csv.DictReader(infile))
        total_rows = len(reader)
        fieldnames = list(reader[0].keys()) + ['Latitude', 'Longitude'] if total_rows > 0 else []

    mode = 'a' if processed_count > 0 else 'w'
    
    with open(OUTPUT_FILE, mode, encoding='utf-8', newline='') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        if mode == 'w':
            writer.writeheader()
            
        for i, row in enumerate(reader):
            # Skip rows we have already processed
            if i < processed_count:
                continue
                
            name = row.get('Truckstop Name', '')
            address = row.get('Address', '')
            city = row.get('City', '')
            state = row.get('State', '')
            
            lat, lng = get_coordinates(name, address, city, state)
            
            row['Latitude'] = lat if lat else ''
            row['Longitude'] = lng if lng else ''
            
            # Write immediately to disk (Fault Tolerance)
            writer.writerow(row)
            outfile.flush()
            
            if lat and lng:
                logging.info(f"[{i+1}/{total_rows}] SUCCESS: {name} -> ({lat}, {lng})")
            else:
                logging.info(f"[{i+1}/{total_rows}] FAILED: {name}")
                
            # Strict sleep to comply with 1-request-per-second limit
            time.sleep(1.2)

if __name__ == '__main__':
    logging.info("Starting Geocoding process...")
    main()
