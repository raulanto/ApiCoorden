from celery import shared_task
from django.core.mail import send_mail
from .models import *
from .services import *


@shared_task
def procesar_levantamiento_topografico(volumen_id):
    """Procesa archivo de levantamiento topográfico"""
    volumen = VolumenTerraceria.objects.get(id=volumen_id)

    # Leer archivo CSV del levantamiento
    import csv
    puntos = []

    with open(volumen.archivo_levantamiento.path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            puntos.append({
                'lat': float(row['lat']),
                'lon': float(row['lon']),
                'elevation': float(row['elevation'])
            })

    # Calcular volúmenes
    service = VolumeCalculationService()
    resultado = service.calculate_by_grid(puntos)

    # Actualizar registro
    volumen.volumen_corte_m3 = resultado['cut']
    volumen.volumen_relleno_m3 = resultado['fill']
    volumen.volumen_neto_m3 = resultado['net']
    volumen.save()

    return f"Procesados {len(puntos)} puntos"


@shared_task
def enviar_alertas_elementos_atrasados():
    """Envía alertas diarias de elementos atrasados"""
    from django.utils import timezone
    hoy = timezone.now().date()

    elementos_atrasados = ElementoConstructivo.objects.filter(
        fecha_fin_programada__lt=hoy,
        estado__in=['PENDIENTE', 'REPLANTEO', 'EXCAVACION']
    )

    for elemento in elementos_atrasados:
        dias_atraso = (hoy - elemento.fecha_fin_programada).days

        # Enviar email al responsable
        if elemento.responsable and elemento.responsable.email:
            send_mail(
                subject=f'Alerta: Elemento {elemento.codigo} con {dias_atraso} días de atraso',
                message=f'El elemento {elemento.nombre} tiene {dias_atraso} días de atraso.',
                from_email='notificaciones@obra.com',
                recipient_list=[elemento.responsable.email]
            )

    return f"Enviadas {elementos_atrasados.count()} alertas"


@shared_task
def actualizar_coordenadas_utm_proyecto(proyecto_id):
    """Convierte todas las coordenadas de un proyecto a UTM"""
    proyecto = Proyecto.objects.get(id=proyecto_id)
    elementos = proyecto.elementos.all()

    coords = [{'lat': e.latitud, 'lon': e.longitud} for e in elementos]
    service = CoordinateTransformService()
    utm_coords = service.wgs84_to_utm_bulk(coords)

    for elemento, utm in zip(elementos, utm_coords):
        elemento.utm_este = utm['easting']
        elemento.utm_norte = utm['northing']
        elemento.utm_zona = utm['zone']
        elemento.save()

    return f"Actualizados {len(elementos)} elementos"