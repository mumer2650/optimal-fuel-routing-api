import os
import pandas as pd
import numpy as np
from sklearn.neighbors import BallTree
from django.conf import settings

class StationDataManager:
    """
    Singleton class to hold our in-memory Pandas DataFrame and BallTree.
    This prevents the app from reloading the CSV on every request.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StationDataManager, cls).__new__(cls)
            cls._instance.df = None
            cls._instance.tree = None
            # We don't automatically load here to prevent issues during Django migrations.
            # We will call .load() explicitly on startup.
        return cls._instance

    def load(self):
        # We only want to load it once
        if self.tree is not None:
            return

        csv_path = os.path.join(settings.BASE_DIR, 'data', 'fuel-prices-geocoded.csv')
        
        # Safety check while your script is still running
        if not os.path.exists(csv_path):
            print(f"Warning: {csv_path} not found. Station tree not loaded.")
            return

        print("Loading gas station dataset into memory...")
        self.df = pd.read_csv(csv_path)
        
        # Drop rows where geocoding failed (NaN coordinates)
        self.df = self.df.dropna(subset=['Latitude', 'Longitude'])
        
        # Reset index so the BallTree integer indices align perfectly with the DataFrame
        self.df = self.df.reset_index(drop=True)
        
        # Convert Lat/Lng to radians. This is REQUIRED for the Haversine metric.
        # Order must be [Latitude, Longitude]
        coords = np.radians(self.df[['Latitude', 'Longitude']].values)
        
        print("Building BallTree spatial index...")
        self.tree = BallTree(coords, metric='haversine')
        
        print(f"Successfully loaded {len(self.df)} stations into the in-memory backend.")

    def get_nearby_stations(self, lat, lng, radius_miles=2.0):
        """
        Queries the BallTree for stations within the given radius (in miles).
        Returns a Pandas DataFrame of the results.
        """
        if self.tree is None:
            raise ValueError("Station data not loaded. Check if the CSV exists.")
            
        # Earth's radius in miles
        EARTH_RADIUS_MILES = 3958.8
        
        # Convert query point and radius to radians
        query_point = np.radians([[lat, lng]])
        radius_radians = radius_miles / EARTH_RADIUS_MILES
        
        # query_radius returns an array of arrays. We grab the first (and only) one.
        indices = self.tree.query_radius(query_point, r=radius_radians)[0]
        
        # Return the subset of the dataframe matching those indices
        return self.df.iloc[indices]

    def get_nearest_station(self, lat, lng):
        """
        Queries the BallTree for the absolute closest station to a point.
        Used to find the required 'Mile 0' starting fuel stop.
        """
        if self.tree is None:
            raise ValueError("Station data not loaded.")
            
        query_point = np.radians([[lat, lng]])
        # query returns (distances, indices). We want the first index of the first result.
        dist, ind = self.tree.query(query_point, k=1)
        
        return self.df.iloc[ind[0]]

# Create a global instance that our API views will import
station_db = StationDataManager()
