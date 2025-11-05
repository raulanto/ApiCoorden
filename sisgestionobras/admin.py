from django.contrib import admin

from unfold.admin import ModelAdmin
from django.utils.html import format_html
from .models import Proyecto, ElementoConstructivo, PuntoControl, Cuadrilla, ReporteAvance, VolumenTerraceria


@admin.register(Proyecto)
class ProyectoAdmin(ModelAdmin):
    list_display = ['codigo', 'nombre', 'cliente', 'estado', 'avance_display', 'created_at']
    list_filter = ['estado', 'sistema_coordenadas']
    search_fields = ['codigo', 'nombre', 'cliente']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Información General', {
            'fields': ('codigo', 'nombre', 'descripcion', 'cliente', 'estado')
        }),
        ('Configuración de Coordenadas', {
            'fields': ('sistema_coordenadas', 'zona_utm', 'hemisferio',
                       'lat_referencia', 'lon_referencia', 'elevacion_referencia')
        }),
        ('Responsables', {
            'fields': ('director_obra', 'residente_obra')
        }),
        ('Fechas y Presupuesto', {
            'fields': ('fecha_inicio', 'fecha_fin_estimada', 'fecha_fin_real', 'presupuesto_total')
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def avance_display(self, obj):
        elementos = obj.elementos.all()
        if not elementos:
            return "0%"
        avance = sum(e.porcentaje_avance for e in elementos) / len(elementos)
        color = 'green' if avance >= 80 else 'orange' if avance >= 50 else 'red'
        # SOLUCIÓN: Formatear el número ANTES de pasarlo a format_html
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}%</span>',
            color, f'{avance:.1f}'  # ← Formatear aquí
        )
    avance_display.short_description = 'Avance'


@admin.register(ElementoConstructivo)
class ElementoConstructivoAdmin(ModelAdmin):
    list_display = ['codigo', 'nombre', 'tipo', 'proyecto', 'estado', 'porcentaje_avance', 'responsable']
    list_filter = ['tipo', 'estado', 'proyecto']
    search_fields = ['codigo', 'nombre']
    readonly_fields = ['utm_este', 'utm_norte', 'utm_zona', 'created_at', 'updated_at']

    fieldsets = (
        ('Identificación', {
            'fields': ('proyecto', 'codigo', 'nombre', 'tipo')
        }),
        ('Coordenadas WGS84', {
            'fields': ('latitud', 'longitud', 'elevacion')
        }),
        ('Coordenadas UTM (Auto)', {
            'fields': ('utm_este', 'utm_norte', 'utm_zona'),
            'classes': ('collapse',)
        }),
        ('Geometría', {
            'fields': ('area_proyecto', 'volumen_proyecto', 'longitud_proyecto')
        }),
        ('Control de Avance', {
            'fields': ('estado', 'porcentaje_avance', 'responsable')
        }),
        ('Programación', {
            'fields': ('fecha_inicio_programada', 'fecha_inicio_real',
                       'fecha_fin_programada', 'fecha_fin_real')
        }),
    )


@admin.register(PuntoControl)
class PuntoControlAdmin(ModelAdmin):
    list_display = ['numero_punto', 'tipo', 'proyecto', 'equipo_medicion', 'validado', 'fecha_medicion']
    list_filter = ['tipo', 'equipo_medicion', 'validado', 'proyecto']
    search_fields = ['numero_punto', 'descripcion']
    readonly_fields = ['fecha_medicion']

    actions = ['validar_puntos']

    def validar_puntos(self, request, queryset):
        from django.utils import timezone
        queryset.update(
            validado=True,
            validado_por=request.user,
            fecha_validacion=timezone.now()
        )
        self.message_user(request, f'{queryset.count()} puntos validados')

    validar_puntos.short_description = 'Validar puntos seleccionados'


@admin.register(Cuadrilla)
class CuadrillaAdmin(ModelAdmin):
    list_display = ['nombre', 'proyecto', 'jefe_cuadrilla', 'activa', 'ultima_actualizacion']
    list_filter = ['activa', 'proyecto']
    search_fields = ['nombre']


@admin.register(ReporteAvance)
class ReporteAvanceAdmin(ModelAdmin):
    list_display = ['elemento', 'fecha', 'avance_porcentaje', 'reportado_por', 'validado']
    list_filter = ['validado', 'fecha', 'elemento__proyecto']
    search_fields = ['elemento__codigo', 'descripcion']
    readonly_fields = ['fecha', 'hora']


@admin.register(VolumenTerraceria)
class VolumenTerraceriaAdmin(ModelAdmin):
    list_display = ['nombre', 'proyecto', 'metodo_calculo', 'volumen_neto_m3', 'fecha_calculo']
    list_filter = ['metodo_calculo', 'proyecto']
    search_fields = ['nombre']
    readonly_fields = ['fecha_calculo']