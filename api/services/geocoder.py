import requests
import logging

logger = logging.getLogger(__name__)

class GeocoderClient:
    """
    A simple client for OpenStreetMap's Nominatim Geocoding API.
    Used to convert city names or addresses (e.g., "Austin, TX") into lat/lng coordinates.
    """
    BASE_URL = "https://nominatim.openstreetmap.org/search"
    
    @classmethod
    def geocode(cls, location_str):
        """
        Takes a string location and returns a tuple of (lat, lng).
        Raises ValueError if the location cannot be found.
        """
        # Use a standard browser User-Agent to avoid getting blocked by Nominatim's strict policies
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        params = {
            'q': location_str,
            'format': 'json',
            'limit': 1
        }
        
        try:
            logger.info(f"Geocoding text location: {location_str}")
            response = requests.get(cls.BASE_URL, params=params, headers=headers, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            if not data:
                raise ValueError(f"Could not find coordinates for location: '{location_str}'")
                
            # Nominatim returns strings for lat/lon
            lat = float(data[0]['lat'])
            lng = float(data[0]['lon'])
            
            logger.info(f"Geocoded '{location_str}' to {lat}, {lng}")
            return lat, lng
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Geocoding API request failed: {e}")
            raise ValueError("Failed to connect to the geocoding service. Please use raw lat,lng coordinates instead.")
