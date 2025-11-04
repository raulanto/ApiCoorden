# Clonar repositorio
git clone <tu-repo>
cd coordinate-api

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Aplicar migraciones
python manage.py migrate

# Crear superusuario (opcional)
python manage.py createsuperuser

# Ejecutar servidor
python manage.py runserver

## Endpoints Disponibles

### 1. Conversión a Web Mercator
```http
POST /api/coordinates/convert/web-mercator/
Content-Type: application/json

{
  "latitude": 19.4326,
  "longitude": -99.1332
}
```

### 2. Conversión a UTM
```http
POST /api/coordinates/convert/utm/
Content-Type: application/json

{
  "latitude": 19.4326,
  "longitude": -99.1332
}
```

### 3. Conversión desde Web Mercator
```http
POST /api/coordinates/convert/from-web-mercator/
Content-Type: application/json

{
  "x": -11035709.89,
  "y": 2195819.58
}
```

### 4. Calcular Distancia
```http
POST /api/coordinates/distance/
Content-Type: application/json

{
  "point1_lat": 19.4326,
  "point1_lon": -99.1332,
  "point2_lat": 25.6866,
  "point2_lon": -100.3161,
  "unit": "km"
}
```

### 5. Generar Bounding Box
```http
POST /api/coordinates/bounding-box/
Content-Type: application/json

{
  "center_lat": 19.4326,
  "center_lon": -99.1332,
  "radius_km": 10
}
```

### 6. Conversión por Lotes
```http
POST /api/coordinates/batch-convert/
Content-Type: application/json

{
  "coordinates": [
    {"latitude": 19.4326, "longitude": -99.1332},
    {"latitude": 25.6866, "longitude": -100.3161}
  ],
  "to_system": "web_mercator"
}
```

### 7. Información Completa
```http
GET /api/coordinates/info/?lat=19.4326&lon=-99.1332
```

## 🧪 Ejecutar Tests

```bash
python manage.py test
```

## 📊 Casos de Uso

### Geofencing para Delivery
```python
# Verificar si cliente está dentro del área de entrega
distance = calculate_distance(restaurant, customer)
if distance <= delivery_radius:
    return "Entrega disponible"
```

### Cálculo de Rutas
```python
# Calcular distancia total de múltiples waypoints
total_distance = sum(distances_between_consecutive_points)
```

### Búsqueda Espacial
```python
# Encontrar puntos dentro de un área
bbox = generate_bounding_box(center, radius)
points_in_area = filter_points_by_bbox(all_points, bbox)
```

## 🌐 Sistemas de Coordenadas Soportados

### WGS84 (EPSG:4326)
- Sistema estándar GPS
- Formato: latitud/longitud en grados
- Rango: Lat [-90, 90], Lon [-180, 180]

### UTM (Universal Transverse Mercator)
- Mediciones en metros
- Dividido en zonas de 6° de longitud
- Ideal para topografía y cartografía

### Web Mercator (EPSG:3857)
- Usado en mapas web (Google, OSM)
- Proyección cilíndrica
- Optimizado para visualización
