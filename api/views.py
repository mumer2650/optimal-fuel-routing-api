from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services.osrm_client import OSRMClient
from .services.routing_engine import RoutingEngine
from .services.optimizer import FuelOptimizer
import logging

logger = logging.getLogger(__name__)

class RouteOptimizationView(APIView):
    """
    GET /api/route/?start=Y,X&finish=Y,X
    Example: /api/route/?start=34.05,-118.24&finish=40.71,-74.00
    """
    
    def get(self, request):
        start = request.query_params.get('start')
        finish = request.query_params.get('finish')
        
        if not start or not finish:
            return Response(
                {"error": "Please provide both 'start' and 'finish' query parameters in 'lat,lng' format."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            start_lat, start_lng = map(float, start.split(','))
            finish_lat, finish_lng = map(float, finish.split(','))
        except ValueError:
            return Response(
                {"error": "Coordinates must be in 'lat,lng' format (e.g., 34.05,-118.24)."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # Phase 2: Fetch Route from OSRM
            route_data = OSRMClient.get_route(start_lat, start_lng, finish_lat, finish_lng)
            geometry = route_data['geometry']
            total_distance = route_data['distance_miles']
            
            # Phase 3 & 4: Spatial Filtering and Linear Referencing
            stations = RoutingEngine.process_route(geometry, start_lat, start_lng, search_radius_miles=2.0)
            
            # Phase 5: Calculate optimal stops using the Greedy Algorithm
            optimization_result = FuelOptimizer.calculate_optimal_stops(stations, total_distance)
            
            # Phase 6: Construct Final JSON Payload
            response_data = {
                "route_geometry": geometry,
                "total_distance_miles": round(total_distance, 2),
                "total_fuel_cost_usd": optimization_result['total_fuel_cost_usd'],
                "fuel_stops": optimization_result['fuel_stops']
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except ValueError as e:
            # Catch known validation errors (e.g., Route impossible)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Internal server error: {e}", exc_info=True)
            return Response(
                {"error": "An internal server error occurred while processing the route."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
