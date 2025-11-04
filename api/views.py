# views.py
import math

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializer import CoordinateSerializer, WebMercatorSerializer, BoundingBoxSerializer, \
    DistanceCalculationSerializer


class CoordinateConverter:
    """Utilidades para conversión de coordenadas"""

    @staticmethod
    def latlon_to_web_mercator(lat, lon):
        """Convierte WGS84 a Web Mercator (EPSG:3857)"""
        x = lon * 20037508.34 / 180
        y = math.log(math.tan((90 + lat) * math.pi / 360)) / (math.pi / 180)
        y = y * 20037508.34 / 180
        return {'x': x, 'y': y}

    @staticmethod
    def web_mercator_to_latlon(x, y):
        """Convierte Web Mercator a WGS84"""
        lon = (x / 20037508.34) * 180
        lat = (y / 20037508.34) * 180
        lat = 180 / math.pi * (2 * math.atan(math.exp(lat * math.pi / 180)) - math.pi / 2)
        return {'latitude': lat, 'longitude': lon}

    @staticmethod
    def latlon_to_utm(lat, lon):
        """Conversión simplificada de WGS84 a UTM"""
        zone = int((lon + 180) / 6) + 1
        letter = 'N' if lat >= 0 else 'S'

        # Conversión aproximada (para producción usar pyproj)
        lon_origin = (zone - 1) * 6 - 180 + 3
        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon - lon_origin)

        a = 6378137.0  # Radio ecuatorial WGS84
        k0 = 0.9996

        N = a / math.sqrt(1 - 0.00669438 * math.sin(lat_rad) ** 2)
        T = math.tan(lat_rad) ** 2
        C = 0.00673949675659 * math.cos(lat_rad) ** 2
        A = math.cos(lat_rad) * lon_rad

        easting = k0 * N * (A + (1 - T + C) * A ** 3 / 6) + 500000
        northing = k0 * (a * lat_rad) + (3000000 if lat < 0 else 0)

        return {
            'zone': zone,
            'letter': letter,
            'easting': easting,
            'northing': northing
        }

    @staticmethod
    def haversine_distance(lat1, lon1, lat2, lon2, unit='km'):
        """Calcula distancia entre dos puntos usando fórmula de Haversine"""
        R = 6371  # Radio de la Tierra en km

        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c

        if unit == 'miles':
            distance *= 0.621371
        elif unit == 'meters':
            distance *= 1000

        return distance


class ConvertToWebMercatorView(APIView):
    """
    POST /api/coordinates/convert/web-mercator/
    Convierte coordenadas WGS84 a Web Mercator
    """

    def post(self, request):
        serializer = CoordinateSerializer(data=request.data)
        if serializer.is_valid():
            result = CoordinateConverter.latlon_to_web_mercator(
                serializer.validated_data['latitude'],
                serializer.validated_data['longitude']
            )
            return Response({
                'input': serializer.validated_data,
                'output': result,
                'system': 'EPSG:3857'
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ConvertToUTMView(APIView):
    """
    POST /api/coordinates/convert/utm/
    Convierte coordenadas WGS84 a UTM
    """

    def post(self, request):
        serializer = CoordinateSerializer(data=request.data)
        if serializer.is_valid():
            result = CoordinateConverter.latlon_to_utm(
                serializer.validated_data['latitude'],
                serializer.validated_data['longitude']
            )
            return Response({
                'input': serializer.validated_data,
                'output': result,
                'system': 'UTM'
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ConvertFromWebMercatorView(APIView):
    """
    POST /api/coordinates/convert/from-web-mercator/
    Convierte Web Mercator a WGS84
    """

    def post(self, request):
        serializer = WebMercatorSerializer(data=request.data)
        if serializer.is_valid():
            result = CoordinateConverter.web_mercator_to_latlon(
                serializer.validated_data['x'],
                serializer.validated_data['y']
            )
            return Response({
                'input': serializer.validated_data,
                'output': result,
                'system': 'WGS84'
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CalculateDistanceView(APIView):
    """
    POST /api/coordinates/distance/
    Calcula distancia entre dos puntos
    """

    def post(self, request):
        serializer = DistanceCalculationSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            distance = CoordinateConverter.haversine_distance(
                data['point1_lat'], data['point1_lon'],
                data['point2_lat'], data['point2_lon'],
                data.get('unit', 'km')
            )
            return Response({
                'point1': {
                    'latitude': data['point1_lat'],
                    'longitude': data['point1_lon']
                },
                'point2': {
                    'latitude': data['point2_lat'],
                    'longitude': data['point2_lon']
                },
                'distance': round(distance, 2),
                'unit': data.get('unit', 'km')
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BoundingBoxView(APIView):
    """
    POST /api/coordinates/bounding-box/
    Calcula un bounding box alrededor de un punto
    """

    def post(self, request):
        serializer = BoundingBoxSerializer(data=request.data)
        if serializer.is_valid():
            lat = serializer.validated_data['center_lat']
            lon = serializer.validated_data['center_lon']
            radius = serializer.validated_data['radius_km']

            # Aproximación simple
            lat_delta = radius / 111.32  # 1 grado ≈ 111.32 km
            lon_delta = radius / (111.32 * math.cos(math.radians(lat)))

            return Response({
                'center': {'latitude': lat, 'longitude': lon},
                'radius_km': radius,
                'bounding_box': {
                    'north': lat + lat_delta,
                    'south': lat - lat_delta,
                    'east': lon + lon_delta,
                    'west': lon - lon_delta,
                    'northeast': {'lat': lat + lat_delta, 'lon': lon + lon_delta},
                    'southwest': {'lat': lat - lat_delta, 'lon': lon - lon_delta}
                }
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def batch_convert_view(request):
    """
    POST /api/coordinates/batch-convert/
    Convierte múltiples coordenadas de una vez
    Body: {
        "coordinates": [{"latitude": 19.4326, "longitude": -99.1332}, ...],
        "to_system": "web_mercator" | "utm"
    }
    """
    coordinates = request.data.get('coordinates', [])
    to_system = request.data.get('to_system', 'web_mercator')

    if not coordinates:
        return Response(
            {'error': 'Se requiere el campo coordinates'},
            status=status.HTTP_400_BAD_REQUEST
        )

    results = []
    for coord in coordinates:
        serializer = CoordinateSerializer(data=coord)
        if serializer.is_valid():
            if to_system == 'web_mercator':
                converted = CoordinateConverter.latlon_to_web_mercator(
                    serializer.validated_data['latitude'],
                    serializer.validated_data['longitude']
                )
            elif to_system == 'utm':
                converted = CoordinateConverter.latlon_to_utm(
                    serializer.validated_data['latitude'],
                    serializer.validated_data['longitude']
                )
            else:
                return Response(
                    {'error': 'Sistema no soportado'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            results.append({
                'input': serializer.validated_data,
                'output': converted
            })
        else:
            results.append({
                'input': coord,
                'error': serializer.errors
            })

    return Response({
        'total': len(coordinates),
        'successful': len([r for r in results if 'error' not in r]),
        'results': results
    })


@api_view(['GET'])
def coordinate_info_view(request):
    """
    GET /api/coordinates/info/?lat=19.4326&lon=-99.1332
    Obtiene información completa sobre una coordenada
    """
    try:
        lat = float(request.query_params.get('lat'))
        lon = float(request.query_params.get('lon'))
    except (TypeError, ValueError):
        return Response(
            {'error': 'Parámetros lat y lon requeridos'},
            status=status.HTTP_400_BAD_REQUEST
        )

    web_merc = CoordinateConverter.latlon_to_web_mercator(lat, lon)
    utm = CoordinateConverter.latlon_to_utm(lat, lon)

    return Response({
        'wgs84': {
            'latitude': lat,
            'longitude': lon,
            'format_dms': f"{abs(lat):.4f}°{'N' if lat >= 0 else 'S'}, {abs(lon):.4f}°{'E' if lon >= 0 else 'W'}"
        },
        'web_mercator': web_merc,
        'utm': utm,
        'hemisphere': 'Northern' if lat >= 0 else 'Southern',
        'timezone_approx': f"UTC{int(lon / 15):+d}"
    })
