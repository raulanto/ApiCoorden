from datetime import datetime, timedelta

import requests
from django.db.models import Avg
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from sisgestionobras.api.serializers import ProyectoSerializer, ElementoConstructivoSerializer, PuntoControlSerializer, \
    CuadrillaSerializer, ReporteAvanceSerializer, VolumenTerraceriaSerializer
from sisgestionobras.models import Proyecto, ElementoConstructivo, PuntoControl, Cuadrilla, ReporteAvance, \
    VolumenTerraceria


class ProyectoViewSet(viewsets.ModelViewSet):
    queryset = Proyecto.objects.all()
    serializer_class = ProyectoSerializer

    @action(detail=True, methods=['get'])
    def dashboard(self, request, pk=None):
        """Dashboard general del proyecto"""
        proyecto = self.get_object()
        elementos = proyecto.elementos.all()

        # Calcular estadísticas
        total_elementos = elementos.count()
        terminados = elementos.filter(estado='TERMINADO').count()
        en_proceso = elementos.exclude(estado__in=['TERMINADO', 'PENDIENTE']).count()
        atrasados = elementos.filter(
            fecha_fin_programada__lt=datetime.now().date(),
            estado__in=['PENDIENTE', 'REPLANTEO', 'EXCAVACION']
        ).count()

        avance_general = elementos.aggregate(Avg('porcentaje_avance'))['porcentaje_avance__avg'] or 0

        return Response({
            'proyecto': ProyectoSerializer(proyecto).data,
            'estadisticas': {
                'total_elementos': total_elementos,
                'terminados': terminados,
                'en_proceso': en_proceso,
                'atrasados': atrasados,
                'avance_general': round(avance_general, 2)
            },
            'elementos_criticos': ElementoConstructivoSerializer(
                elementos.filter(estado__in=['REPLANTEO', 'EXCAVACION']).order_by('fecha_fin_programada')[:5],
                many=True
            ).data
        })

    @action(detail=True, methods=['post'])
    def convertir_coordenadas_proyecto(self, request, pk=None):
        """Convierte todas las coordenadas del proyecto a UTM"""
        proyecto = self.get_object()
        API_BASE = 'http://localhost:8000/api'  # Tu API de coordenadas

        coordenadas = []
        for elemento in proyecto.elementos.all():
            coordenadas.append({
                'id': str(elemento.id),
                'latitude': elemento.latitud,
                'longitude': elemento.longitud
            })

        # Llamar a tu API de conversión por lotes
        response = requests.post(
            f'{API_BASE}/coordinates/batch-convert/',
            json={
                'coordinates': [{'latitude': c['latitude'], 'longitude': c['longitude']} for c in coordenadas],
                'to_system': 'utm'
            }
        )

        if response.status_code == 200:
            resultados = response.json()['results']

            # Actualizar elementos con coordenadas UTM
            for coord_original, resultado in zip(coordenadas, resultados):
                elemento = ElementoConstructivo.objects.get(id=coord_original['id'])
                elemento.utm_este = resultado['output']['easting']
                elemento.utm_norte = resultado['output']['northing']
                elemento.utm_zona = resultado['output']['zone']
                elemento.save()

            return Response({
                'message': f'Se convirtieron {len(coordenadas)} elementos a UTM',
                'zona_utm': resultados[0]['output']['zone'] if resultados else None
            })

        return Response(
            {'error': 'Error al convertir coordenadas'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class ElementoConstructivoViewSet(viewsets.ModelViewSet):
    queryset = ElementoConstructivo.objects.all()
    serializer_class = ElementoConstructivoSerializer

    @action(detail=True, methods=['get'])
    def distancia_a_benchmark(self, request, pk=None):
        """Calcula distancia del elemento al benchmark del proyecto"""
        elemento = self.get_object()
        proyecto = elemento.proyecto

        API_BASE = 'http://localhost:8000/api'

        response = requests.post(
            f'{API_BASE}/coordinates/distance/',
            json={
                'point1_lat': proyecto.lat_referencia,
                'point1_lon': proyecto.lon_referencia,
                'point2_lat': elemento.latitud,
                'point2_lon': elemento.longitud,
                'unit': 'meters'
            }
        )

        if response.status_code == 200:
            data = response.json()
            return Response({
                'elemento': elemento.codigo,
                'benchmark': 'BM Principal',
                'distancia_metros': data['distance'],
                'coordenadas_elemento': {
                    'lat': elemento.latitud,
                    'lon': elemento.longitud
                },
                'coordenadas_benchmark': {
                    'lat': proyecto.lat_referencia,
                    'lon': proyecto.lon_referencia
                }
            })

        return Response({'error': 'Error al calcular distancia'}, status=500)

    @action(detail=False, methods=['post'])
    def elementos_en_area(self, request):
        """Encuentra elementos dentro de un radio desde un punto"""
        lat = request.data.get('lat')
        lon = request.data.get('lon')
        radio_km = request.data.get('radio_km', 1)
        proyecto_id = request.data.get('proyecto_id')

        if not all([lat, lon, proyecto_id]):
            return Response(
                {'error': 'Se requieren lat, lon y proyecto_id'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Obtener bounding box
        API_BASE = 'http://localhost:8000/api'
        response = requests.post(
            f'{API_BASE}/coordinates/bounding-box/',
            json={
                'center_lat': float(lat),
                'center_lon': float(lon),
                'radius_km': float(radio_km)
            }
        )

        if response.status_code == 200:
            bbox = response.json()['bounding_box']

            # Filtrar elementos dentro del bbox
            elementos = ElementoConstructivo.objects.filter(
                proyecto_id=proyecto_id,
                latitud__gte=bbox['south'],
                latitud__lte=bbox['north'],
                longitud__gte=bbox['west'],
                longitud__lte=bbox['east']
            )

            return Response({
                'centro': {'lat': lat, 'lon': lon},
                'radio_km': radio_km,
                'total_elementos': elementos.count(),
                'elementos': ElementoConstructivoSerializer(elementos, many=True).data
            })

        return Response({'error': 'Error al calcular área'}, status=500)


class PuntoControlViewSet(viewsets.ModelViewSet):
    queryset = PuntoControl.objects.all()
    serializer_class = PuntoControlSerializer

    @action(detail=False, methods=['post'])
    def registrar_medicion(self, request):
        """Registra un nuevo punto de control desde campo"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            punto = serializer.save(topografo=request.user)
            return Response({
                'message': 'Punto registrado exitosamente',
                'punto': PuntoControlSerializer(punto).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CuadrillaViewSet(viewsets.ModelViewSet):
    queryset = Cuadrilla.objects.all()
    serializer_class = CuadrillaSerializer

    @action(detail=True, methods=['post'])
    def actualizar_ubicacion(self, request, pk=None):
        """Actualiza ubicación en tiempo real de la cuadrilla"""
        cuadrilla = self.get_object()
        lat = request.data.get('lat')
        lon = request.data.get('lon')

        if not all([lat, lon]):
            return Response(
                {'error': 'Se requieren lat y lon'},
                status=status.HTTP_400_BAD_REQUEST
            )

        cuadrilla.latitud_actual = lat
        cuadrilla.longitud_actual = lon
        cuadrilla.ultima_actualizacion = datetime.now()
        cuadrilla.save()

        return Response({
            'message': 'Ubicación actualizada',
            'cuadrilla': CuadrillaSerializer(cuadrilla).data
        })

    @action(detail=False, methods=['get'])
    def mapa_cuadrillas(self, request):
        """Obtiene ubicaciones de todas las cuadrillas activas"""
        proyecto_id = request.query_params.get('proyecto_id')

        cuadrillas = Cuadrilla.objects.filter(activa=True)
        if proyecto_id:
            cuadrillas = cuadrillas.filter(proyecto_id=proyecto_id)

        # Filtrar solo cuadrillas con ubicación actualizada en las últimas 2 horas
        dos_horas_atras = datetime.now() - timedelta(hours=2)
        cuadrillas = cuadrillas.filter(
            ultima_actualizacion__gte=dos_horas_atras
        ).exclude(latitud_actual__isnull=True)

        return Response({
            'total_cuadrillas': cuadrillas.count(),
            'cuadrillas': CuadrillaSerializer(cuadrillas, many=True).data
        })


class ReporteAvanceViewSet(viewsets.ModelViewSet):
    queryset = ReporteAvance.objects.all()
    serializer_class = ReporteAvanceSerializer

    @action(detail=False, methods=['post'])
    def crear_reporte_campo(self, request):
        """Crear reporte desde app móvil de campo"""
        data = request.data.copy()
        data['reportado_por'] = request.user.id

        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            reporte = serializer.save()

            # Actualizar porcentaje del elemento
            elemento = reporte.elemento
            elemento.porcentaje_avance = reporte.avance_porcentaje
            if reporte.avance_porcentaje >= 100:
                elemento.estado = 'TERMINADO'
                elemento.fecha_fin_real = datetime.now().date()
            elemento.save()

            return Response({
                'message': 'Reporte creado exitosamente',
                'reporte': ReporteAvanceSerializer(reporte).data
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def reportes_proyecto(self, request):
        """Obtiene todos los reportes de un proyecto"""
        proyecto_id = request.query_params.get('proyecto_id')
        fecha_desde = request.query_params.get('fecha_desde')
        fecha_hasta = request.query_params.get('fecha_hasta')

        reportes = ReporteAvance.objects.filter(
            elemento__proyecto_id=proyecto_id
        )

        if fecha_desde:
            reportes = reportes.filter(fecha__gte=fecha_desde)
        if fecha_hasta:
            reportes = reportes.filter(fecha__lte=fecha_hasta)

        return Response({
            'total_reportes': reportes.count(),
            'reportes': ReporteAvanceSerializer(reportes, many=True).data
        })


class VolumenTerraceriaViewSet(viewsets.ModelViewSet):
    queryset = VolumenTerraceria.objects.all()
    serializer_class = VolumenTerraceriaSerializer

    @action(detail=False, methods=['post'])
    def calcular_volumenes(self, request):
        """
        Calcula volúmenes de corte y relleno a partir de levantamiento

        Expected data:
        {
            "proyecto_id": "uuid",
            "nombre": "Cálculo Terracería Zona A",
            "metodo_calculo": "GRID",
            "puntos": [
                {"lat": 19.4326, "lon": -99.1332, "elevacion": 2240.5},
                ...
            ],
            "elevacion_proyecto": 2242.0
        }
        """
        proyecto_id = request.data.get('proyecto_id')
        nombre = request.data.get('nombre')
        metodo = request.data.get('metodo_calculo', 'GRID')
        puntos = request.data.get('puntos', [])
        elevacion_proyecto = request.data.get('elevacion_proyecto')

        if not all([proyecto_id, nombre, puntos, elevacion_proyecto]):
            return Response(
                {'error': 'Faltan datos requeridos'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Cálculo simplificado (en producción usar algoritmos más sofisticados)
        total_puntos = len(puntos)
        area_punto = 100  # m² por punto (aproximación)

        volumen_corte = 0
        volumen_relleno = 0

        for punto in puntos:
            dif_elevacion = punto['elevacion'] - elevacion_proyecto
            volumen = abs(dif_elevacion) * area_punto

            if dif_elevacion > 0:
                volumen_corte += volumen
            else:
                volumen_relleno += volumen

        # Crear registro
        volumen = VolumenTerraceria.objects.create(
            proyecto_id=proyecto_id,
            nombre=nombre,
            metodo_calculo=metodo,
            area_m2=total_puntos * area_punto,
            volumen_corte_m3=volumen_corte,
            volumen_relleno_m3=volumen_relleno,
            volumen_neto_m3=volumen_corte - volumen_relleno,
            calculado_por=request.user
        )

        return Response({
            'message': 'Volúmenes calculados exitosamente',
            'volumen': VolumenTerraceriaSerializer(volumen).data,
            'resumen': {
                'puntos_procesados': total_puntos,
                'area_total_m2': total_puntos * area_punto,
                'corte_m3': round(volumen_corte, 2),
                'relleno_m3': round(volumen_relleno, 2),
                'neto_m3': round(volumen_corte - volumen_relleno, 2),
                'compensacion': 'Compensado' if abs(volumen_corte - volumen_relleno) < 100 else 'No compensado'
            }
        })
