import polyline
import numpy as np
import pandas as pd
from math import radians, cos, sin, asin, sqrt
from .station_data import station_db
import logging

logger = logging.getLogger(__name__)

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points in miles.
    """
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    return c * 3958.8

class RoutingEngine:
    @classmethod
    def process_route(cls, geometry_str, start_lat, start_lng, search_radius_miles=2.0):
        """
        Decodes the polyline, downsamples it, finds nearby stations via spatial filtering, 
        and snaps them to exact mile markers along the route (Linear Referencing).
        """
        logger.info("Decoding route geometry...")
        # 1. Decode the OSRM polyline (returns a list of (lat, lng) tuples)
        route_coords = polyline.decode(geometry_str)
        
        # Calculate the cumulative distance (mile marker) for every single point on the route
        cumulative_distances = [0.0]
        for i in range(1, len(route_coords)):
            dist = haversine_distance(
                route_coords[i-1][0], route_coords[i-1][1],
                route_coords[i][0], route_coords[i][1]
            )
            cumulative_distances.append(cumulative_distances[-1] + dist)

        total_distance = cumulative_distances[-1]
        logger.info(f"Route is {total_distance:.2f} miles long. Downsampling for spatial search...")

        # 2. Downsampling: We only query the BallTree ~once every 2 miles to save CPU
        sampled_indices = [0]
        last_sampled_dist = 0.0
        
        for i, dist in enumerate(cumulative_distances):
            if dist - last_sampled_dist >= search_radius_miles:
                sampled_indices.append(i)
                last_sampled_dist = dist
        
        # Ensure the final destination point is always included
        if sampled_indices[-1] != len(route_coords) - 1:
            sampled_indices.append(len(route_coords) - 1)

        # 3. Spatial Filtering
        logger.info("Querying spatial index for nearby gas stations...")
        nearby_stations_dfs = []
        unique_station_ids = set()

        # THE MILE 0 REQUIREMENT: The vehicle must fill up immediately.
        # We find the absolute closest station to the start coordinate and force it to be Mile 0.
        try:
            start_station = station_db.get_nearest_station(start_lat, start_lng).copy()
            # It's returned as a Pandas Series, convert to single-row DataFrame
            start_station_df = pd.DataFrame([start_station])
            start_station_df['mile_marker'] = 0.0
            nearby_stations_dfs.append(start_station_df)
            unique_station_ids.add(start_station['OPIS Truckstop ID'])
        except Exception as e:
            logger.error(f"Failed to find starting station: {e}")
            raise ValueError("Could not find a starting gas station near the origin.")

        # Search around all downsampled points
        for idx in sampled_indices:
            lat, lng = route_coords[idx]
            stations = station_db.get_nearby_stations(lat, lng, radius_miles=search_radius_miles)
            
            # Filter out stations we have already processed
            new_stations = stations[~stations['OPIS Truckstop ID'].isin(unique_station_ids)]
            
            if not new_stations.empty:
                new_stations = new_stations.copy()
                
                # 4. Linear Referencing (Snapping to the polyline)
                mile_markers = []
                # Vectorized setup for fast Haversine against the full route
                route_array = np.radians(np.array(route_coords))
                route_lats = route_array[:, 0]
                route_lngs = route_array[:, 1]
                
                for _, station in new_stations.iterrows():
                    s_lat, s_lng = np.radians(station['Latitude']), np.radians(station['Longitude'])
                    
                    dlon = route_lngs - s_lng
                    dlat = route_lats - s_lat
                    a = np.sin(dlat/2.0)**2 + np.cos(s_lat) * np.cos(route_lats) * np.sin(dlon/2.0)**2
                    c = 2 * np.arcsin(np.sqrt(a))
                    distances = 3958.8 * c
                    
                    # Find the exact polyline point that is closest to this gas station
                    closest_idx = np.argmin(distances)
                    mile_markers.append(cumulative_distances[closest_idx])
                
                new_stations['mile_marker'] = mile_markers
                unique_station_ids.update(new_stations['OPIS Truckstop ID'].tolist())
                nearby_stations_dfs.append(new_stations)

        # 5. Combine and Sort
        if not nearby_stations_dfs:
            raise ValueError("No gas stations found along this route.")

        all_stations = pd.concat(nearby_stations_dfs, ignore_index=True)
        
        # Sort by mile marker ascending (creating the 1D Array)
        all_stations = all_stations.sort_values('mile_marker').reset_index(drop=True)
        
        logger.info(f"Found {len(all_stations)} unique gas stations along the route.")
        
        # Return as a list of dictionaries for the Optimizer to consume
        return all_stations.to_dict('records')
