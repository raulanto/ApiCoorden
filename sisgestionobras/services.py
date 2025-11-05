import math
import numpy as np
from typing import List, Dict, Tuple
from sisgestionobras.models import Proyecto, ElementoConstructivo

class CoordinateTransformService:
    """Servicio para transformaciones de coordenadas avanzadas"""

    @staticmethod
    def wgs84_to_utm_bulk(coordinates: List[Dict]) -> List[Dict]:
        """
        Convierte lote de coordenadas WGS84 a UTM

        Args:
            coordinates: [{"lat": float, "lon": float}, ...]

        Returns:
            [{"este": float, "norte": float, "zona": int}, ...]
        """
        import requests
        API_BASE = 'http://localhost:8000/api'

        response = requests.post(
            f'{API_BASE}/coordinates/batch-convert/',
            json={
                'coordinates': [{'latitude': c['lat'], 'longitude': c['lon']} for c in coordinates],
                'to_system': 'utm'
            }
        )

        if response.status_code == 200:
            results = response.json()['results']
            return [r['output'] for r in results]
        return []

    @staticmethod
    def calculate_area_polygon(points: List[Tuple[float, float]]) -> float:
        """
        Calcula área de polígono usando fórmula de Shoelace

        Args:
            points: [(lat1, lon1), (lat2, lon2), ...]

        Returns:
            Área en m²
        """
        if len(points) < 3:
            return 0

        # Convertir a UTM para cálculos en metros
        coords_utm = CoordinateTransformService.wgs84_to_utm_bulk([
            {'lat': p[0], 'lon': p[1]} for p in points
        ])

        # Fórmula de Shoelace
        x = [c['easting'] for c in coords_utm]
        y = [c['northing'] for c in coords_utm]

        area = 0.5 * abs(sum(x[i] * y[i + 1] - x[i + 1] * y[i] for i in range(len(x) - 1)))
        return area


class VolumeCalculationService:
    """Servicio para cálculo de volúmenes de terracería"""

    @staticmethod
    def calculate_by_grid(points: List[Dict], grid_size: float = 10) -> Dict:
        """
        Cálculo de volúmenes por método de retícula

        Args:
            points: [{"lat": float, "lon": float, "elevation": float}, ...]
            grid_size: Tamaño de celda en metros

        Returns:
            {"cut": float, "fill": float, "net": float}
        """
        # Implementación simplificada
        # En producción usar interpolación más sofisticada

        total_cut = 0
        total_fill = 0

        for point in points:
            # Calcular diferencia con elevación de proyecto
            # Este valor vendría del frontend
            diff = point.get('diff_elevation', 0)
            volume = abs(diff) * (grid_size ** 2)

            if diff > 0:
                total_cut += volume
            else:
                total_fill += volume

        return {
            'cut': total_cut,
            'fill': total_fill,
            'net': total_cut - total_fill
        }

    @staticmethod
    def calculate_by_sections(sections: List[Dict]) -> Dict:
        """
        Cálculo de volúmenes por método de áreas extremas

        Args:
            sections: [{"area_cut": float, "area_fill": float, "distance": float}, ...]

        Returns:
            {"cut": float, "fill": float}
        """
        total_cut = 0
        total_fill = 0

        for i in range(len(sections) - 1):
            sec1 = sections[i]
            sec2 = sections[i + 1]
            dist = sec2['distance'] - sec1['distance']

            # Fórmula de áreas extremas
            avg_cut = (sec1['area_cut'] + sec2['area_cut']) / 2
            avg_fill = (sec1['area_fill'] + sec2['area_fill']) / 2

            total_cut += avg_cut * dist
            total_fill += avg_fill * dist

        return {
            'cut': total_cut,
            'fill': total_fill,
            'net': total_cut - total_fill
        }


class GeofenceService:
    """Servicio para geofencing y alertas"""

    @staticmethod
    def is_point_in_project_area(lat: float, lon: float, proyecto: Proyecto) -> bool:
        """Verifica si un punto está dentro del área del proyecto"""
        import requests

        # Obtener bounding box del proyecto (basado en elementos)
        elementos = proyecto.elementos.all()
        if not elementos:
            return False

        lats = [e.latitud for e in elementos]
        lons = [e.longitud for e in elementos]

        # Expandir 10% el bbox para margen
        lat_min, lat_max = min(lats) * 0.9999, max(lats) * 1.0001
        lon_min, lon_max = min(lons) * 0.9999, max(lons) * 1.0001

        return (lat_min <= lat <= lat_max) and (lon_min <= lon <= lon_max)

    @staticmethod
    def get_nearest_element(lat: float, lon: float, proyecto_id: str) -> ElementoConstructivo:
        """Encuentra el elemento más cercano a una ubicación"""
        import requests

        elementos = ElementoConstructivo.objects.filter(proyecto_id=proyecto_id)
        API_BASE = 'http://localhost:8000/api'

        min_distance = float('inf')
        nearest = None

        for elemento in elementos:
            response = requests.post(
                f'{API_BASE}/coordinates/distance/',
                json={
                    'point1_lat': lat,
                    'point1_lon': lon,
                    'point2_lat': elemento.latitud,
                    'point2_lon': elemento.longitud,
                    'unit': 'meters'
                }
            )

            if response.status_code == 200:
                distance = response.json()['distance']
                if distance < min_distance:
                    min_distance = distance
                    nearest = elemento

        return nearest, min_distance