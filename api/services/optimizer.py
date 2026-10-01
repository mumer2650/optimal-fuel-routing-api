import logging

logger = logging.getLogger(__name__)

class FuelOptimizer:
    """
    Implements the Greedy Algorithm to find the mathematically optimal fuel stops.
    Assumptions:
    - Max Range: 500 miles
    - MPG: 10
    - Capacity: 50 gallons
    - Starting state: 0 gallons (empty)
    """
    MAX_RANGE_MILES = 500.0
    MPG = 10.0

    @classmethod
    def calculate_optimal_stops(cls, stations, total_route_distance):
        stops = []
        total_cost = 0.0
        
        current_fuel_miles = 0.0
        current_station_idx = 0
        
        logger.info("Executing Greedy Algorithm on the 1D station array...")
        
        while True:
            current_station = stations[current_station_idx]
            current_mile = current_station['mile_marker']
            current_price = current_station['Retail Price']
            
            dist_to_finish = total_route_distance - current_mile
            
            # Rule 1 (Finish Line): Can we reach the destination from here?
            if dist_to_finish <= cls.MAX_RANGE_MILES:
                miles_needed = dist_to_finish - current_fuel_miles
                if miles_needed > 0:
                    gallons_to_buy = miles_needed / cls.MPG
                    cost = gallons_to_buy * current_price
                    total_cost += cost
                    
                    stops.append({
                        "station_name": current_station.get('Truckstop Name', 'Unknown Station'),
                        "location": {"lat": current_station['Latitude'], "lng": current_station['Longitude']},
                        "gallons_purchased": round(gallons_to_buy, 2),
                        "price_per_gallon": round(current_price, 3),
                        "stop_cost": round(cost, 2)
                    })
                break
                
            # Build the 500-mile lookahead window
            window_stations = []
            for j in range(current_station_idx + 1, len(stations)):
                s = stations[j]
                if s['mile_marker'] <= current_mile + cls.MAX_RANGE_MILES:
                    window_stations.append((j, s))
                else:
                    break
                    
            # Rule 4 (Stranded)
            if not window_stations:
                logger.error(f"Stranded at mile {current_mile:.2f}. No stations within 500 miles.")
                raise ValueError("Route is impossible. The gap between gas stations exceeds the 500-mile max range.")
                
            # Rule 2 (Delay): Is there a cheaper station within the window?
            # If so, target the FIRST one. Buy exactly enough to arrive empty.
            cheaper_station_found = False
            for j, s in window_stations:
                if s['Retail Price'] < current_price:
                    target_idx = j
                    target_mile = s['mile_marker']
                    
                    dist_to_target = target_mile - current_mile
                    miles_to_buy = dist_to_target - current_fuel_miles
                    
                    if miles_to_buy > 0:
                        gallons_to_buy = miles_to_buy / cls.MPG
                        cost = gallons_to_buy * current_price
                        total_cost += cost
                        
                        stops.append({
                            "station_name": current_station.get('Truckstop Name', 'Unknown Station'),
                            "location": {"lat": current_station['Latitude'], "lng": current_station['Longitude']},
                            "gallons_purchased": round(gallons_to_buy, 2),
                            "price_per_gallon": round(current_price, 3),
                            "stop_cost": round(cost, 2)
                        })
                        
                        current_fuel_miles = 0.0 # We arrive at the target perfectly empty
                    else:
                        # We already have enough fuel in the tank to reach it
                        current_fuel_miles -= dist_to_target
                        
                    current_station_idx = target_idx
                    cheaper_station_found = True
                    break
            
            if cheaper_station_found:
                continue
                
            # Rule 3 (Hoard): All stations in the window are MORE expensive than us.
            # Fill the tank to absolute MAX capacity, and drive to the LEAST expensive station in the window.
            best_target_idx = -1
            best_target_price = float('inf')
            
            for j, s in window_stations:
                if s['Retail Price'] < best_target_price:
                    best_target_price = s['Retail Price']
                    best_target_idx = j
                    
            target_station = stations[best_target_idx]
            target_mile = target_station['mile_marker']
            
            miles_to_buy = cls.MAX_RANGE_MILES - current_fuel_miles
            if miles_to_buy > 0:
                gallons_to_buy = miles_to_buy / cls.MPG
                cost = gallons_to_buy * current_price
                total_cost += cost
                
                stops.append({
                    "station_name": current_station.get('Truckstop Name', 'Unknown Station'),
                    "location": {"lat": current_station['Latitude'], "lng": current_station['Longitude']},
                    "gallons_purchased": round(gallons_to_buy, 2),
                    "price_per_gallon": round(current_price, 3),
                    "stop_cost": round(cost, 2)
                })
                
            dist_to_target = target_mile - current_mile
            current_fuel_miles = cls.MAX_RANGE_MILES - dist_to_target
            current_station_idx = best_target_idx
            
        logger.info(f"Optimization complete. Total fuel cost: ${total_cost:.2f}")
        return {
            "total_fuel_cost_usd": round(total_cost, 2),
            "fuel_stops": stops
        }
