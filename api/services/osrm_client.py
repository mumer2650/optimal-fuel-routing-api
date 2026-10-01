import requests
import logging

logger = logging.getLogger(__name__)

class OSRMClient:
    """
    A service client to interact with the Open Source Routing Machine (OSRM) public API.
    This handles our single permitted external API call per request.
    """
    BASE_URL = "https://router.project-osrm.org/route/v1/driving"

    @classmethod
    def get_route(cls, start_lat, start_lng, finish_lat, finish_lng):
        """
        Fetches the optimal driving route geometry and distance.
        Note: OSRM strictly expects coordinates in Longitude,Latitude order!
        """
        coordinates = f"{start_lng},{start_lat};{finish_lng},{finish_lat}"
        url = f"{cls.BASE_URL}/{coordinates}"
        
        # 'overview=full' ensures we get the detailed, high-resolution polyline needed for snapping
        # 'geometries=polyline' returns the standard encoded string
        params = {
            "overview": "full",
            "geometries": "polyline"
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") != "Ok":
                logger.error(f"OSRM API Error: {data.get('message', 'Unknown error')}")
                raise ValueError("Could not find a valid driving route between these locations.")
                
            route = data["routes"][0]
            
            # OSRM returns distance in meters. We convert this to miles.
            # 1 meter = 0.000621371 miles
            distance_meters = route["distance"]
            distance_miles = distance_meters * 0.000621371
            
            return {
                "geometry": route["geometry"],
                "distance_miles": distance_miles
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"OSRM API Request failed: {str(e)}")
            raise Exception("Routing service is currently unavailable or the coordinates are invalid.")
