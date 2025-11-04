import requests
import json

BASE_URL = 'http://localhost:8000'


# ============================================
# 1. Convertir WGS84 a Web Mercator
# ============================================
def example_web_mercator():
    url = f'{BASE_URL}/api/coordinates/convert/web-mercator/'
    data = {
        'latitude': 19.4326,  # Ciudad de México
        'longitude': -99.1332
    }
    response = requests.post(url, json=data)
    print("🌐 Conversión a Web Mercator:")
    print(json.dumps(response.json(), indent=2))
    print()


# ============================================
# 2. Convertir WGS84 a UTM
# ============================================
def example_utm():
    url = f'{BASE_URL}/api/coordinates/convert/utm/'
    data = {
        'latitude': 19.4326,
        'longitude': -99.1332
    }
    response = requests.post(url, json=data)
    print("📍 Conversión a UTM:")
    print(json.dumps(response.json(), indent=2))
    print()


# ============================================
# 3. Calcular distancia entre dos puntos
# ============================================
def example_distance():
    url = f'{BASE_URL}/api/coordinates/distance/'
    data = {
        'point1_lat': 19.4326,  # CDMX
        'point1_lon': -99.1332,
        'point2_lat': 25.6866,  # Monterrey
        'point2_lon': -100.3161,
        'unit': 'km'
    }
    response = requests.post(url, json=data)
    print("📏 Distancia entre CDMX y Monterrey:")
    print(json.dumps(response.json(), indent=2))
    print()


# ============================================
# 4. Calcular Bounding Box
# ============================================
def example_bounding_box():
    url = f'{BASE_URL}/api/coordinates/bounding-box/'
    data = {
        'center_lat': 19.4326,
        'center_lon': -99.1332,
        'radius_km': 5  # 5 km de radio
    }
    response = requests.post(url, json=data)
    print("📦 Bounding Box (5km de radio):")
    print(json.dumps(response.json(), indent=2))
    print()


# ============================================
# 5. Conversión por lotes
# ============================================
def example_batch_conversion():
    url = f'{BASE_URL}/api/coordinates/batch-convert/'
    data = {
        'coordinates': [
            {'latitude': 19.4326, 'longitude': -99.1332},  # CDMX
            {'latitude': 25.6866, 'longitude': -100.3161},  # Monterrey
            {'latitude': 20.6597, 'longitude': -103.3496},  # Guadalajara
            {'latitude': 21.1619, 'longitude': -86.8515},  # Cancún
        ],
        'to_system': 'web_mercator'
    }
    response = requests.post(url, json=data)
    print("🔄 Conversión por lotes:")
    print(json.dumps(response.json(), indent=2))
    print()


# ============================================
# 6. Información completa de una coordenada
# ============================================
def example_coordinate_info():
    url = f'{BASE_URL}/api/coordinates/info/'
    params = {
        'lat': 19.4326,
        'lon': -99.1332
    }
    response = requests.get(url, params=params)
    print("ℹ️ Información completa de coordenada:")
    print(json.dumps(response.json(), indent=2))
    print()


# ============================================
# 7. Convertir de Web Mercator a WGS84
# ============================================
def example_from_web_mercator():
    url = f'{BASE_URL}/api/coordinates/convert/from-web-mercator/'
    data = {
        'x': -11035709.89,
        'y': 2195819.58
    }
    response = requests.post(url, json=data)
    print("🔄 Conversión desde Web Mercator:")
    print(json.dumps(response.json(), indent=2))
    print()


# ============================================
# Casos de uso avanzados
# ============================================

def advanced_example_geofencing():
    """
    Ejemplo: Sistema de geofencing para delivery
    Verifica si un punto está dentro de un área de entrega
    """
    print("🎯 Caso de uso: Geofencing para delivery")

    # Centro del restaurante
    restaurant = {'lat': 19.4326, 'lon': -99.1332}
    delivery_radius_km = 5

    # Ubicación del cliente
    customer = {'lat': 19.4500, 'lon': -99.1200}

    # Calcular distancia
    url = f'{BASE_URL}/api/coordinates/distance/'
    data = {
        'point1_lat': restaurant['lat'],
        'point1_lon': restaurant['lon'],
        'point2_lat': customer['lat'],
        'point2_lon': customer['lon'],
        'unit': 'km'
    }
    response = requests.post(url, json=data)
    distance = response.json()['distance']

    if distance <= delivery_radius_km:
        print(f"✅ Cliente dentro del área de entrega ({distance:.2f} km)")
    else:
        print(f"❌ Cliente fuera del área de entrega ({distance:.2f} km)")
    print()


def advanced_example_route_waypoints():
    """
    Ejemplo: Calcular distancia total de una ruta con múltiples puntos
    """
    print("🗺️ Caso de uso: Distancia total de ruta")

    waypoints = [
        {'name': 'CDMX', 'lat': 19.4326, 'lon': -99.1332},
        {'name': 'Querétaro', 'lat': 20.5888, 'lon': -100.3899},
        {'name': 'Guadalajara', 'lat': 20.6597, 'lon': -103.3496},
        {'name': 'Monterrey', 'lat': 25.6866, 'lon': -100.3161}
    ]

    total_distance = 0
    url = f'{BASE_URL}/api/coordinates/distance/'

    for i in range(len(waypoints) - 1):
        data = {
            'point1_lat': waypoints[i]['lat'],
            'point1_lon': waypoints[i]['lon'],
            'point2_lat': waypoints[i + 1]['lat'],
            'point2_lon': waypoints[i + 1]['lon'],
            'unit': 'km'
        }
        response = requests.post(url, json=data)
        segment_distance = response.json()['distance']
        total_distance += segment_distance

        print(f"  {waypoints[i]['name']} → {waypoints[i + 1]['name']}: {segment_distance:.2f} km")

    print(f"\n📊 Distancia total: {total_distance:.2f} km")
    print()


if __name__ == '__main__':
    print("=" * 60)
    print("   API DE COORDENADAS - EJEMPLOS DE USO")
    print("=" * 60)
    print()

    # Ejecutar ejemplos básicos
    example_web_mercator()
    example_utm()
    example_distance()
    example_bounding_box()
    example_batch_conversion()
    example_coordinate_info()
    example_from_web_mercator()

    # Ejecutar ejemplos avanzados
    advanced_example_geofencing()
    advanced_example_route_waypoints()