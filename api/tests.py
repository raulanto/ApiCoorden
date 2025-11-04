# tests.py
from rest_framework.test import APITestCase
from rest_framework import status
import json


class CoordinateAPITestCase(APITestCase):

    def test_convert_to_web_mercator(self):
        """Prueba conversión a Web Mercator"""
        url = '/api/coordinates/convert/web-mercator/'
        data = {
            'latitude': 19.4326,
            'longitude': -99.1332
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('output', response.data)
        self.assertIn('x', response.data['output'])
        self.assertIn('y', response.data['output'])

    def test_convert_to_utm(self):
        """Prueba conversión a UTM"""
        url = '/api/coordinates/convert/utm/'
        data = {
            'latitude': 19.4326,
            'longitude': -99.1332
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('zone', response.data['output'])
        self.assertIn('easting', response.data['output'])
        self.assertIn('northing', response.data['output'])

    def test_calculate_distance(self):
        """Prueba cálculo de distancia"""
        url = '/api/coordinates/distance/'
        data = {
            'point1_lat': 19.4326,
            'point1_lon': -99.1332,
            'point2_lat': 25.6866,
            'point2_lon': -100.3161,
            'unit': 'km'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('distance', response.data)
        self.assertGreater(response.data['distance'], 0)

    def test_bounding_box(self):
        """Prueba cálculo de bounding box"""
        url = '/api/coordinates/bounding-box/'
        data = {
            'center_lat': 19.4326,
            'center_lon': -99.1332,
            'radius_km': 10
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('bounding_box', response.data)
        self.assertIn('north', response.data['bounding_box'])

    def test_batch_convert(self):
        """Prueba conversión por lotes"""
        url = '/api/coordinates/batch-convert/'
        data = {
            'coordinates': [
                {'latitude': 19.4326, 'longitude': -99.1332},
                {'latitude': 25.6866, 'longitude': -100.3161},
                {'latitude': 20.6597, 'longitude': -103.3496}
            ],
            'to_system': 'web_mercator'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total'], 3)
        self.assertEqual(response.data['successful'], 3)

    def test_coordinate_info(self):
        """Prueba información completa de coordenada"""
        url = '/api/coordinates/info/?lat=19.4326&lon=-99.1332'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('wgs84', response.data)
        self.assertIn('web_mercator', response.data)
        self.assertIn('utm', response.data)

    def test_invalid_latitude(self):
        """Prueba validación de latitud inválida"""
        url = '/api/coordinates/convert/web-mercator/'
        data = {
            'latitude': 95,  # Inválido
            'longitude': -99.1332
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

