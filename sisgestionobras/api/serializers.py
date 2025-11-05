from rest_framework import serializers

from sisgestionobras.models import Proyecto, ElementoConstructivo, PuntoControl, Cuadrilla, ReporteAvance, \
    VolumenTerraceria


class ProyectoSerializer(serializers.ModelSerializer):
    director_nombre = serializers.CharField(source='director_obra.get_full_name', read_only=True)
    residente_nombre = serializers.CharField(source='residente_obra.get_full_name', read_only=True)
    total_elementos = serializers.IntegerField(source='elementos.count', read_only=True)
    avance_general = serializers.SerializerMethodField()

    class Meta:
        model = Proyecto
        fields = '__all__'

    def get_avance_general(self, obj):
        elementos = obj.elementos.all()
        if not elementos:
            return 0
        return sum(e.porcentaje_avance for e in elementos) / len(elementos)


class ElementoConstructivoSerializer(serializers.ModelSerializer):
    proyecto_nombre = serializers.CharField(source='proyecto.nombre', read_only=True)
    responsable_nombre = serializers.CharField(source='responsable.get_full_name', read_only=True)
    coordenadas_utm = serializers.SerializerMethodField()
    dias_atraso = serializers.SerializerMethodField()

    class Meta:
        model = ElementoConstructivo
        fields = '__all__'

    def get_coordenadas_utm(self, obj):
        if obj.utm_este and obj.utm_norte:
            return {
                'este': obj.utm_este,
                'norte': obj.utm_norte,
                'zona': obj.utm_zona
            }
        return None

    def get_dias_atraso(self, obj):
        from django.utils import timezone
        if obj.fecha_fin_programada and obj.estado != 'TERMINADO':
            hoy = timezone.now().date()
            if hoy > obj.fecha_fin_programada:
                return (hoy - obj.fecha_fin_programada).days
        return 0


class PuntoControlSerializer(serializers.ModelSerializer):
    elemento_codigo = serializers.CharField(source='elemento.codigo', read_only=True)
    topografo_nombre = serializers.CharField(source='topografo.get_full_name', read_only=True)

    class Meta:
        model = PuntoControl
        fields = '__all__'


class CuadrillaSerializer(serializers.ModelSerializer):
    jefe_nombre = serializers.CharField(source='jefe_cuadrilla.get_full_name', read_only=True)
    elemento_actual_codigo = serializers.CharField(source='elemento_actual.codigo', read_only=True)
    ubicacion_actual = serializers.SerializerMethodField()

    class Meta:
        model = Cuadrilla
        fields = '__all__'

    def get_ubicacion_actual(self, obj):
        if obj.latitud_actual and obj.longitud_actual:
            return {
                'lat': obj.latitud_actual,
                'lon': obj.longitud_actual,
                'ultima_actualizacion': obj.ultima_actualizacion
            }
        return None


class ReporteAvanceSerializer(serializers.ModelSerializer):
    elemento_codigo = serializers.CharField(source='elemento.codigo', read_only=True)
    reportado_por_nombre = serializers.CharField(source='reportado_por.get_full_name', read_only=True)

    class Meta:
        model = ReporteAvance
        fields = '__all__'


class VolumenTerraceriaSerializer(serializers.ModelSerializer):
    calculado_por_nombre = serializers.CharField(source='calculado_por.get_full_name', read_only=True)
    balance = serializers.SerializerMethodField()

    class Meta:
        model = VolumenTerraceria
        fields = '__all__'

    def get_balance(self, obj):
        return {
            'corte': obj.volumen_corte_m3,
            'relleno': obj.volumen_relleno_m3,
            'neto': obj.volumen_neto_m3,
            'tipo': 'Compensado' if abs(obj.volumen_neto_m3) < 100 else (
                'Corte' if obj.volumen_neto_m3 > 0 else 'Relleno')
        }
