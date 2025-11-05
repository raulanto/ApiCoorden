from datetime import timedelta
from django.utils.safestring import mark_safe
from django.contrib import admin
from django.db.models import Avg
from django.shortcuts import render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import (
    RangeDateFilter,
    RangeNumericFilter,
    ChoicesDropdownFilter,
)
from unfold.decorators import display
import json
from .models import Proyecto, ElementoConstructivo, PuntoControl, Cuadrilla, ReporteAvance, VolumenTerraceria
from django.contrib.admin import AdminSite


class ProyectoResource(resources.ModelResource):
    class Meta:
        model = Proyecto
        fields = ('codigo', 'nombre', 'cliente', 'estado', 'fecha_inicio',
                  'fecha_fin_estimada', 'presupuesto_total')
        export_order = fields


class ElementoResource(resources.ModelResource):
    proyecto_codigo = fields.Field(
        column_name='proyecto_codigo',
        attribute='proyecto__codigo'
    )

    class Meta:
        model = ElementoConstructivo
        fields = ('codigo', 'nombre', 'tipo', 'proyecto_codigo', 'latitud',
                  'longitud', 'estado', 'porcentaje_avance')


class ElementoInline(TabularInline):
    model = ElementoConstructivo
    extra = 0
    fields = ['codigo', 'nombre', 'tipo', 'estado', 'porcentaje_avance_display']
    readonly_fields = ['porcentaje_avance_display']
    can_delete = False
    show_change_link = True

    @display(description="Avance", ordering="porcentaje_avance")
    def porcentaje_avance_display(self, obj):
        if not obj.pk:
            return "-"
        color = 'success' if obj.porcentaje_avance >= 80 else 'warning' if obj.porcentaje_avance >= 50 else 'danger'
        return format_html(
            '<span class="badge badge-{}">{:.1f}%</span>',
            color, obj.porcentaje_avance
        )


class PuntoControlInline(TabularInline):
    model = PuntoControl
    extra = 0
    fields = ['numero_punto', 'tipo', 'equipo_medicion', 'validado']
    readonly_fields = []
    can_delete = True


class ReporteInline(TabularInline):
    model = ReporteAvance
    extra = 0
    fields = ['fecha', 'avance_porcentaje', 'reportado_por', 'validado']
    readonly_fields = ['fecha', 'reportado_por']
    can_delete = False
    show_change_link = True


# ============================================
# PROYECTO ADMIN - CORREGIDO
# ============================================

@admin.register(Proyecto)
class ProyectoAdmin(ModelAdmin, ImportExportModelAdmin):
    resource_class = ProyectoResource

    list_display = [
        'codigo',
        'nombre_display',
        'cliente',
        'estado_badge',
        'avance_display',
        'presupuesto_display',
        'dias_restantes',
        'acciones'
    ]

    list_filter = [
        ('estado', ChoicesDropdownFilter),
        ('sistema_coordenadas', ChoicesDropdownFilter),
        ('fecha_inicio', RangeDateFilter),
        ('presupuesto_total', RangeNumericFilter),
    ]

    search_fields = ['codigo', 'nombre', 'cliente']

    readonly_fields = [
        'created_at',
        'updated_at',
        'estadisticas_card',
        'mapa_proyecto',
    ]

    fieldsets = (
        ('Información General', {
            'fields': ('codigo', 'nombre', 'descripcion', 'cliente', 'estado'),
            'classes': ['tab'],
        }),
        ('Configuración Geográfica', {
            'fields': (
                'sistema_coordenadas',
                ('zona_utm', 'hemisferio'),
                ('lat_referencia', 'lon_referencia'),
                'elevacion_referencia',
                'mapa_proyecto',
            ),
            'classes': ['tab'],
        }),
        ('Gestión del Proyecto', {
            'fields': (
                ('director_obra', 'residente_obra'),
                ('fecha_inicio', 'fecha_fin_estimada', 'fecha_fin_real'),
                'presupuesto_total',
                'estadisticas_card',
            ),
            'classes': ['tab'],
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ['tab'],
        }),
    )

    inlines = [ElementoInline]
    actions = ['exportar_dashboard', 'calcular_volumenes']

    @display(description="Proyecto", ordering="nombre")
    def nombre_display(self, obj):
        return format_html(
            '<strong>{}</strong><br/><small class="text-muted">{}</small>',
            obj.nombre,
            obj.codigo
        )

    @display(description="Estado", ordering="estado")
    def estado_badge(self, obj):
        colors = {
            'PLAN': 'info',
            'EJECUCION': 'success',
            'PAUSADO': 'warning',
            'FINALIZADO': 'secondary',
        }
        return format_html(
            '<span class="badge badge-{}">{}</span>',
            colors.get(obj.estado, 'secondary'),
            obj.get_estado_display()
        )

    @display(description="Avance")
    def avance_display(self, obj):
        elementos = obj.elementos.all()
        if not elementos:
            return format_html('<span class="text-muted">Sin elementos</span>')

        avance = sum(e.porcentaje_avance for e in elementos) / len(elementos)
        color = 'success' if avance >= 80 else 'warning' if avance >= 50 else 'danger'

        # CORREGIDO: Formatear el número ANTES
        avance_formateado = round(avance, 1)

        return format_html(
            '''
            <div class="progress" style="height: 20px;">
                <div class="progress-bar bg-{}" role="progressbar" 
                     style="width: {}%" aria-valuenow="{}" aria-valuemin="0" aria-valuemax="100">
                    {}%
                </div>
            </div>
            ''',
            color, avance_formateado, avance_formateado, avance_formateado
        )

    @display(description="Presupuesto", ordering="presupuesto_total")
    def presupuesto_display(self, obj):
        return format_html(
            '<strong>${}</strong><br/><small class="text-muted">MXN</small>',
            f'{obj.presupuesto_total:,.0f}'
        )
    @display(description="Días Restantes")
    def dias_restantes(self, obj):
        if obj.fecha_fin_real:
            return format_html('<span class="badge badge-success">✓ Finalizado</span>')

        hoy = timezone.now().date()
        dias = (obj.fecha_fin_estimada - hoy).days

        if dias < 0:
            return format_html(
                '<span class="badge badge-danger">{} días de atraso</span>',
                abs(dias)
            )
        elif dias < 30:
            return format_html(
                '<span class="badge badge-warning">{} días</span>',
                dias
            )
        else:
            return format_html(
                '<span class="badge badge-info">{} días</span>',
                dias
            )

    @display(description="Acciones")
    def acciones(self, obj):
        return format_html(
            '''
            <a href="{}" class="button" style="padding: 4px 8px; font-size: 12px;">
                Dashboard
            </a>
            <a href="{}" class="button" style="padding: 4px 8px; font-size: 12px;">
             Mapa
            </a>
            ''',
            reverse('admin:proyecto_dashboard', args=[obj.pk]),
            reverse('admin:proyecto_mapa', args=[obj.pk])
        )

    @display(description="Estadísticas del Proyecto")
    def estadisticas_card(self, obj):
        if not obj.pk:
            return "Guarde el proyecto para ver estadísticas"

        elementos = obj.elementos.all()
        total = elementos.count()
        terminados = elementos.filter(estado='TERMINADO').count()
        en_proceso = elementos.exclude(estado__in=['TERMINADO', 'PENDIENTE']).count()
        pendientes = elementos.filter(estado='PENDIENTE').count()

        return format_html(
            '''
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin: 1rem 0;">
                <div style="background: #f0f9ff; padding: 1rem; border-radius: 8px; text-align: center;">
                    <div style="font-size: 2rem; font-weight: bold; color: #0284c7;">{}</div>
                    <div style="color: #64748b; font-size: 0.875rem;">Total Elementos</div>
                </div>
                <div style="background: #f0fdf4; padding: 1rem; border-radius: 8px; text-align: center;">
                    <div style="font-size: 2rem; font-weight: bold; color: #16a34a;">{}</div>
                    <div style="color: #64748b; font-size: 0.875rem;">Terminados</div>
                </div>
                <div style="background: #fef3c7; padding: 1rem; border-radius: 8px; text-align: center;">
                    <div style="font-size: 2rem; font-weight: bold; color: #d97706;">{}</div>
                    <div style="color: #64748b; font-size: 0.875rem;">En Proceso</div>
                </div>
                <div style="background: #fef2f2; padding: 1rem; border-radius: 8px; text-align: center;">
                    <div style="font-size: 2rem; font-weight: bold; color: #dc2626;">{}</div>
                    <div style="color: #64748b; font-size: 0.875rem;">Pendientes</div>
                </div>
            </div>
            ''',
            total, terminados, en_proceso, pendientes
        )

    @display(description="Mapa del Proyecto")
    def mapa_proyecto(self, obj):
        if not obj.pk:
            return "Guarde el proyecto para ver el mapa"

        return format_html(
            '''
            <div id="map-{}" style="height: 400px; border-radius: 8px;"></div>
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
            <script>
                var map = L.map('map-{}').setView([{}, {}], 15);
                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(map);
                L.marker([{}, {}]).addTo(map)
                    .bindPopup('<b>Benchmark Principal</b><br/>Elevación: {}m').openPopup();
            </script>
            ''',
            obj.pk, obj.pk,
            obj.lat_referencia, obj.lon_referencia,
            obj.lat_referencia, obj.lon_referencia,
            obj.elevacion_referencia
        )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:object_id>/dashboard/',
                self.admin_site.admin_view(self.proyecto_dashboard_view),
                name='proyecto_dashboard',
            ),
            path(
                '<path:object_id>/mapa/',
                self.admin_site.admin_view(self.proyecto_mapa_view),
                name='proyecto_mapa',
            ),
        ]
        return custom_urls + urls

    def proyecto_dashboard_view(self, request, object_id):
        proyecto = self.get_object(request, object_id)
        elementos = proyecto.elementos.all()

        context = {
            'proyecto': proyecto,
            'total_elementos': elementos.count(),
            'terminados': elementos.filter(estado='TERMINADO').count(),
            'en_proceso': elementos.exclude(estado__in=['TERMINADO', 'PENDIENTE']).count(),
            'avance_promedio': elementos.aggregate(Avg('porcentaje_avance'))['porcentaje_avance__avg'] or 0,
            'reportes_ultima_semana': 0,
        }

        return render(request, 'admin/proyecto_dashboard.html', context)

    def proyecto_mapa_view(self, request, object_id):
        proyecto = self.get_object(request, object_id)
        elementos = proyecto.elementos.all()

        # Serializar elementos a JSON
        elementos_json = []
        for elemento in elementos:
            elementos_json.append({
                'id': str(elemento.id),
                'codigo': elemento.codigo,
                'nombre': elemento.nombre,
                'latitud': elemento.latitud,
                'longitud': elemento.longitud,
                'estado': elemento.estado,
                'estado_display': elemento.get_estado_display(),
                'porcentaje_avance': float(elemento.porcentaje_avance),
            })

        context = {
            'proyecto': proyecto,
            'elementos': elementos,
            'elementos_json': json.dumps(elementos_json),  # JSON para JavaScript
        }

        return render(request, 'admin/proyecto_mapa.html', context)

    @admin.action(description="Exportar dashboard a PDF")
    def exportar_dashboard(self, request, queryset):
        self.message_user(request, f"{queryset.count()} proyectos exportados")

    @admin.action(description="Calcular volúmenes de terracería")
    def calcular_volumenes(self, request, queryset):
        self.message_user(request, f"Volúmenes calculados para {queryset.count()} proyectos")


# ============================================
# ELEMENTO CONSTRUCTIVO ADMIN - CORREGIDO
# ============================================

@admin.register(ElementoConstructivo)
class ElementoConstructivoAdmin(ModelAdmin, ImportExportModelAdmin):
    resource_class = ElementoResource

    list_display = [
        'codigo',
        'nombre_corto',
        'tipo_badge',
        'proyecto_link',
        'estado_badge',
        'avance_bar',
        'responsable_display',
        'dias_programados',
    ]

    list_filter = [
        ('tipo', ChoicesDropdownFilter),
        ('estado', ChoicesDropdownFilter),
        ('proyecto', admin.RelatedOnlyFieldListFilter),
        ('porcentaje_avance', RangeNumericFilter),
        ('fecha_fin_programada', RangeDateFilter),
    ]

    search_fields = ['codigo', 'nombre', 'proyecto__codigo']

    readonly_fields = [
        'utm_display',
        'coordenadas_card',
        'avance_timeline',
    ]

    fieldsets = (
        ('Identificación', {
            'fields': ('proyecto', 'codigo', 'nombre', 'tipo'),
        }),
        ('Ubicación', {
            'fields': (
                ('latitud', 'longitud', 'elevacion'),
                'utm_display',
                'coordenadas_card',
            ),
        }),
        ('Geometría', {
            'fields': ('area_proyecto', 'volumen_proyecto', 'longitud_proyecto'),
        }),
        ('Control', {
            'fields': (
                ('estado', 'porcentaje_avance'),
                'responsable',
                'avance_timeline',
            ),
        }),
        ('Programación', {
            'fields': (
                ('fecha_inicio_programada', 'fecha_inicio_real'),
                ('fecha_fin_programada', 'fecha_fin_real'),
            ),
        }),
    )

    inlines = [PuntoControlInline, ReporteInline]

    @display(description="Elemento")
    def nombre_corto(self, obj):
        return format_html(
            '<strong>{}</strong><br/><small>{}</small>',
            obj.nombre[:30] + '...' if len(obj.nombre) > 30 else obj.nombre,
            obj.codigo
        )

    @display(description="Tipo", ordering="tipo")
    def tipo_badge(self, obj):
        icons = {
            'ZAPATA': '🏗️',
            'COLUMNA': '🏛️',
            'TRABE': '➖',
            'LOSA': '⬜',
            'MURO': '🧱',
        }
        return format_html(
            '{} {}',
            icons.get(obj.tipo, '📦'),
            obj.get_tipo_display()
        )

    @display(description="Proyecto")
    def proyecto_link(self, obj):
        url = reverse('admin:sisgestionobras_proyecto_change', args=[obj.proyecto.pk])
        return format_html('<a href="{}">{}</a>', url, obj.proyecto.codigo)

    @display(description="Estado", ordering="estado")
    def estado_badge(self, obj):
        colors = {
            'PENDIENTE': 'secondary',
            'REPLANTEO': 'info',
            'EXCAVACION': 'warning',
            'CIMBRADO': 'primary',
            'ARMADO': 'primary',
            'COLADO': 'success',
            'TERMINADO': 'success',
        }
        return format_html(
            '<span class="badge badge-{}">{}</span>',
            colors.get(obj.estado, 'secondary'),
            obj.get_estado_display()
        )

    @display(description="Avance", ordering="porcentaje_avance")
    def avance_bar(self, obj):
        color = 'success' if obj.porcentaje_avance >= 80 else 'warning' if obj.porcentaje_avance >= 50 else 'danger'
        # CORREGIDO: Convertir a int
        porcentaje = int(obj.porcentaje_avance)

        return format_html(
            '''
            <div style="width: 100px;">
                <div class="progress" style="height: 18px;">
                    <div class="progress-bar bg-{}" style="width: {}%">{}%</div>
                </div>
            </div>
            ''',
            color, porcentaje, porcentaje
        )

    @display(description="Responsable")
    def responsable_display(self, obj):
        if obj.responsable:
            return format_html(
                '<span title="{}">{}</span>',
                obj.responsable.get_full_name() or obj.responsable.username,
                obj.responsable.first_name or obj.responsable.username[:10]
            )
        return format_html('<span class="text-muted">Sin asignar</span>')

    @display(description="Programación")
    def dias_programados(self, obj):
        if not obj.fecha_fin_programada:
            return "-"

        hoy = timezone.now().date()
        dias = (obj.fecha_fin_programada - hoy).days

        if obj.estado == 'TERMINADO':
            if obj.fecha_fin_real:
                diferencia = (obj.fecha_fin_real - obj.fecha_fin_programada).days
                if diferencia <= 0:
                    return format_html('<span class="badge badge-success">✓ A tiempo</span>',0)
                else:
                    return format_html('<span class="badge badge-warning">+{} días</span>', diferencia)

        if dias < 0:
            return format_html('<span class="badge badge-danger">⚠️ {} días atraso</span>', abs(dias))
        elif dias < 7:
            return format_html('<span class="badge badge-warning">⏰ {} días</span>', dias)
        else:
            return format_html('<span class="badge badge-info">{} días</span>', dias)

    @display(description="Coordenadas UTM")
    def utm_display(self, obj):
        if obj.utm_este and obj.utm_norte:
            return format_html(
                '''
                <div style="font-family: monospace; background: #f8f9fa; padding: 0.5rem; border-radius: 4px;">
                    <strong>Zona {}:</strong><br/>
                    Este: {} m<br/>
                    Norte: {} m
                </div>
                ''',
                obj.utm_zona, f'{obj.utm_este:.2f}', f'{obj.utm_norte:.2f}'
            )
        return format_html('<span class="text-muted">Calcular UTM</span>')

    @display(description="Tarjeta de Coordenadas")
    def coordenadas_card(self, obj):
        # CORREGIDO: Pre-formatear los valores
        utm_este_str = f'{obj.utm_este:.2f}m' if obj.utm_este else 'N/A'
        utm_norte_str = f'{obj.utm_norte:.2f}m' if obj.utm_norte else 'N/A'
        utm_zona_str = str(obj.utm_zona) if obj.utm_zona else 'N/A'

        return format_html(
            '''
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                <div style="background: #f0f9ff; padding: 1rem; border-radius: 8px;">
                    <div style="font-weight: bold; color: #0284c7; margin-bottom: 0.5rem;">WGS84</div>
                    <div>Lat: {}°</div>
                    <div>Lon: {}°</div>
                    <div>Elev: {}m</div>
                </div>
                <div style="background: #f0fdf4; padding: 1rem; border-radius: 8px;">
                    <div style="font-weight: bold; color: #16a34a; margin-bottom: 0.5rem;">UTM</div>
                    <div>Este: {}</div>
                    <div>Norte: {}</div>
                    <div>Zona: {}</div>
                </div>
            </div>
            ''',
            f'{obj.latitud:.6f}', f'{obj.longitud:.6f}', f'{obj.elevacion:.6f}',
            utm_este_str, utm_norte_str, utm_zona_str
        )

    @display(description="Timeline de Avance")
    def avance_timeline(self, obj):
        if not obj.pk:
            return "Guarde para ver timeline"

        reportes = obj.reportes.order_by('-fecha')[:5]
        if not reportes:
            return format_html('<span class="text-muted">Sin reportes</span>')

        timeline_html = '<div style="border-left: 2px solid #e5e7eb; padding-left: 1rem;">'
        for reporte in reportes:
            # Pre-formatear valores
            avance_str = f'{reporte.avance_porcentaje:.1f}'
            desc_corta = reporte.descripcion[:50]

            timeline_html += f'''
                <div style="margin-bottom: 1rem; position: relative;">
                    <div style="position: absolute; left: -1.5rem; width: 1rem; height: 1rem; 
                                background: #3b82f6; border-radius: 50%; border: 2px solid white;"></div>
                    <div style="font-weight: bold;">{reporte.fecha}</div>
                    <div>Avance: {avance_str}%</div>
                    <div style="font-size: 0.875rem; color: #64748b;">{desc_corta}...</div>
                </div>
            '''
        timeline_html += '</div>'

        # CORREGIDO: Usar mark_safe en lugar de format_html
        return mark_safe(timeline_html)


# ============================================
# CUADRILLA ADMIN
# ============================================

@admin.register(Cuadrilla)
class CuadrillaAdmin(ModelAdmin):
    list_display = [
        'nombre',
        'proyecto_link',
        'jefe_display',
        'elemento_actual_display',
        'ubicacion_display',
        'estado_activo',
        'ultima_actualizacion_display',
    ]

    list_filter = [
        'activa',
        ('proyecto', admin.RelatedOnlyFieldListFilter),
        ('ultima_actualizacion', RangeDateFilter),
    ]

    search_fields = ['nombre', 'jefe_cuadrilla__first_name', 'proyecto__codigo']

    fieldsets = (
        ('Información General', {
            'fields': ('proyecto', 'nombre', 'jefe_cuadrilla', 'activa'),
        }),
        ('Ubicación Actual', {
            'fields': (
                ('latitud_actual', 'longitud_actual'),
                'ultima_actualizacion',
                'elemento_actual',
            ),
        }),
    )

    @display(description="Proyecto")
    def proyecto_link(self, obj):
        url = reverse('admin:sisgestionobras_proyecto_change', args=[obj.proyecto.pk])
        return format_html('<a href="{}">{}</a>', url, obj.proyecto.codigo)

    @display(description="Jefe de Cuadrilla")
    def jefe_display(self, obj):
        if obj.jefe_cuadrilla:
            return format_html(
                '👷 {}',
                obj.jefe_cuadrilla.get_full_name() or obj.jefe_cuadrilla.username
            )
        return mark_safe('<span class="text-muted">Sin jefe</span>')

    @display(description="Trabajando en")
    def elemento_actual_display(self, obj):
        if obj.elemento_actual:
            url = reverse('admin:sisgestionobras_elementoconstructivo_change', args=[obj.elemento_actual.pk])
            return format_html(
                '<a href="{}">{}</a>',
                url, obj.elemento_actual.codigo
            )
        return mark_safe('<span class="text-muted">Sin asignar</span>')

    @display(description="Ubicación GPS")
    def ubicacion_display(self, obj):
        if obj.latitud_actual and obj.longitud_actual:
            return format_html(
                ' <a href="https://www.google.com/maps?q={},{}" target="_blank">Ver mapa</a>',
                obj.latitud_actual, obj.longitud_actual
            )
        return mark_safe('<span class="text-muted">Sin ubicación</span>')

    @display(description="Estado", ordering="activa")
    def estado_activo(self, obj):
        if obj.activa:
            return mark_safe('<span class="badge badge-success">✓ Activa</span>')
        return mark_safe('<span class="badge badge-secondary">Inactiva</span>')

    @display(description="Última Actualización")
    def ultima_actualizacion_display(self, obj):
        if not obj.ultima_actualizacion:
            return mark_safe('<span class="text-muted">Nunca</span>')

        ahora = timezone.now()
        diferencia = ahora - obj.ultima_actualizacion

        if diferencia.total_seconds() < 300:  # 5 minutos
            return format_html('<span class="badge badge-success">Hace {} min</span>',
                               int(diferencia.total_seconds() / 60))
        elif diferencia.total_seconds() < 3600:  # 1 hora
            return format_html('<span class="badge badge-warning">Hace {} min</span>',
                               int(diferencia.total_seconds() / 60))
        else:
            return format_html('<span class="badge badge-danger">Hace {}h</span>',
                               int(diferencia.total_seconds() / 3600))


# ============================================
# REPORTE AVANCE ADMIN
# ============================================

@admin.register(ReporteAvance)
class ReporteAvanceAdmin(ModelAdmin):
    list_display = [
        'elemento_codigo',
        'fecha_hora_display',
        'avance_display',
        'cuadrilla_display',
        'reportado_por_display',
        'validado_badge',
        'ver_foto',
    ]

    list_filter = [
        'validado',
        ('fecha', RangeDateFilter),
        ('elemento__proyecto', admin.RelatedOnlyFieldListFilter),
        ('avance_porcentaje', RangeNumericFilter),
    ]

    search_fields = ['elemento__codigo', 'descripcion', 'reportado_por__username']

    readonly_fields = [
        'fecha',
        'hora',
        'foto_preview',
        'mapa_ubicacion',
    ]

    fieldsets = (
        ('Información del Reporte', {
            'fields': (
                'elemento',
                'cuadrilla',
                ('fecha', 'hora'),
                'reportado_por',
            ),
        }),
        ('Ubicación', {
            'fields': (
                ('latitud', 'longitud'),
                'mapa_ubicacion',
            ),
        }),
        ('Avance', {
            'fields': (
                'avance_cantidad',
                'avance_porcentaje',
                'descripcion',
            ),
        }),
        ('Recursos', {
            'fields': (
                'materiales_utilizados',
                ('personal_asignado', 'horas_trabajadas'),
            ),
        }),
        ('Evidencia', {
            'fields': (
                'foto',
                'foto_preview',
            ),
        }),
        ('Validación', {
            'fields': (
                'validado',
                'validado_por',
            ),
        }),
    )

    actions = ['validar_reportes', 'exportar_reportes']

    @display(description="Elemento")
    def elemento_codigo(self, obj):
        url = reverse('admin:sisgestionobras_elementoconstructivo_change', args=[obj.elemento.pk])
        return format_html('<a href="{}">{}</a>', url, obj.elemento.codigo)

    @display(description="Fecha y Hora", ordering="fecha")
    def fecha_hora_display(self, obj):
        return format_html(
            '<strong>{}</strong><br/><small>{}</small>',
            obj.fecha.strftime('%d/%m/%Y'),
            obj.hora.strftime('%H:%M')
        )

    @display(description="Avance", ordering="avance_porcentaje")
    def avance_display(self, obj):
        color = 'success' if obj.avance_porcentaje >= 80 else 'warning' if obj.avance_porcentaje >= 50 else 'info'
        return format_html(
            '''
            <div style="min-width: 80px;">
                <div class="progress" style="height: 18px;">
                    <div class="progress-bar bg-{}" style="width: {}%">{}%</div>
                </div>
                <small class="text-muted">{} unidades</small>
            </div>
            ''',
            color, f'{obj.avance_porcentaje:,.0f}', f'{obj.avance_porcentaje:,.0f}', f'{obj.avance_cantidad:,.0f}'
        )

    @display(description="Cuadrilla")
    def cuadrilla_display(self, obj):
        if obj.cuadrilla:
            return obj.cuadrilla.nombre
        return format_html('<span class="text-muted">N/A</span>')

    @display(description="Reportado por")
    def reportado_por_display(self, obj):
        if obj.reportado_por:
            return format_html(
                '👤 {}',
                obj.reportado_por.get_full_name() or obj.reportado_por.username
            )
        return '-'

    @display(description="Validado", ordering="validado")
    def validado_badge(self, obj):
        if obj.validado:
            validador = obj.validado_por.get_full_name() if obj.validado_por else 'Sistema'
            return format_html(
                '<span class="badge badge-success" title="Validado por {}">✓</span>',
                validador
            )
        return mark_safe('<span class="badge badge-warning">Pendiente</span>')

    @display(description="Foto")
    def ver_foto(self, obj):
        if obj.foto:
            return format_html(
                '<a href="{}" target="_blank"> Ver</a>',
                obj.foto.url
            )
        return mark_safe('<span class="text-muted">Sin foto</span>')

    @display(description="Vista Previa de Foto")
    def foto_preview(self, obj):
        if obj.foto:
            return format_html(
                '<img src="{}" style="max-width: 400px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">',
                obj.foto.url
            )
        return mark_safe('<span class="text-muted">Sin foto cargada</span>')

    @display(description="Ubicación del Reporte")
    def mapa_ubicacion(self, obj):
        if not obj.latitud or not obj.longitud:
            return "Sin ubicación"

        return format_html(
            '''
            <div id="map-reporte-{}" style="height: 300px; border-radius: 8px;"></div>
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <script>
                var map = L.map('map-reporte-{}').setView([{}, {}], 16);
                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(map);
                L.marker([{}, {}]).addTo(map).bindPopup('Reporte: {}');
            </script>
            <p style="margin-top: 0.5rem;">
                <a href="https://www.google.com/maps?q={},{}" target="_blank">
                    Abrir en Google Maps
                </a>
            </p>
            ''',
            obj.pk, obj.pk,
            obj.latitud, obj.longitud,
            obj.latitud, obj.longitud,
            obj.elemento.codigo,
            obj.latitud, obj.longitud
        )

    @admin.action(description="✓ Validar reportes seleccionados")
    def validar_reportes(self, request, queryset):
        updated = queryset.update(
            validado=True,
            validado_por=request.user
        )
        self.message_user(request, f'{updated} reportes validados', 'success')

    @admin.action(description="📄 Exportar reportes a Excel")
    def exportar_reportes(self, request, queryset):
        # Implementar exportación
        self.message_user(request, f'{queryset.count()} reportes exportados', 'success')

# ============================================
# PUNTO DE CONTROL ADMIN
# ============================================


@admin.register(PuntoControl)
class PuntoControlAdmin(ModelAdmin):
    list_display = [
        'numero_punto',
        'tipo_badge',
        'proyecto_link',
        'elemento_link',
        'equipo_badge',
        'precision_display',
        'validado_badge',
        'fecha_medicion_display',
    ]

    list_filter = [
        ('tipo', ChoicesDropdownFilter),
        ('equipo_medicion', ChoicesDropdownFilter),
        'validado',
        ('fecha_medicion', RangeDateFilter),
    ]

    search_fields = ['numero_punto', 'descripcion', 'proyecto__codigo']

    readonly_fields = ['fecha_medicion', 'coordenadas_detalle', 'mapa_punto']

    fieldsets = (
        ('Identificación', {
            'fields': (
                'proyecto',
                'elemento',
                'numero_punto',
                'descripcion',
                'tipo',
            ),
        }),
        ('Medición', {
            'fields': (
                ('latitud', 'longitud', 'elevacion'),
                ('precision_horizontal', 'precision_vertical'),
                'equipo_medicion',
                'topografo',
                'fecha_medicion',
                'coordenadas_detalle',
                'mapa_punto',
            ),
        }),
        ('Validación', {
            'fields': (
                'validado',
                'validado_por',
                'fecha_validacion',
                'observaciones',
            ),
        }),
    )

    actions = ['validar_puntos']

    @display(description="Punto", ordering="numero_punto")
    def numero_punto(self, obj):
        return format_html('<strong>{}</strong>', obj.numero_punto)

    @display(description="Tipo", ordering="tipo")
    def tipo_badge(self, obj):
        icons = {
            'BENCHMARK': '🎯',
            'REPLANTEO': '📍',
            'VERIFICACION': '✓',
            'CONTROL': '📏',
            'LEVANTAMIENTO': '🗺️',
        }
        colors = {
            'BENCHMARK': 'danger',
            'REPLANTEO': 'primary',
            'VERIFICACION': 'success',
            'CONTROL': 'info',
            'LEVANTAMIENTO': 'warning',
        }
        return format_html(
            '<span class="badge badge-{}">{} {}</span>',
            colors.get(obj.tipo, 'secondary'),
            icons.get(obj.tipo, '📌'),
            obj.get_tipo_display()
        )

    @display(description="Proyecto")
    def proyecto_link(self, obj):
        url = reverse('admin:sisgestionobras_proyecto_change', args=[obj.proyecto.pk])
        return format_html('<a href="{}">{}</a>', url, obj.proyecto.codigo)

    @display(description="Elemento")
    def elemento_link(self, obj):
        if obj.elemento:
            url = reverse('admin:sisgestionobras_elementoconstructivo_change', args=[obj.elemento.pk])
            return format_html('<a href="{}">{}</a>', url, obj.elemento.codigo)
        return format_html('<span class="text-muted">N/A</span>')

    @display(description="Equipo", ordering="equipo_medicion")
    def equipo_badge(self, obj):
        icons = {
            'GPS_DIFERENCIAL': '🛰️',
            'GPS_RTK': '📡',
            'ESTACION_TOTAL': '📐',
            'NIVEL': '🔧',
            'GPS_MOVIL': '📱',
        }
        return format_html(
            '{} {}',
            icons.get(obj.equipo_medicion, '🔧'),
            obj.get_equipo_medicion_display()
        )

    @display(description="Precisión")
    def precision_display(self, obj):
        if obj.precision_horizontal and obj.precision_vertical:
            color_h = 'success' if obj.precision_horizontal <= 2 else 'warning' if obj.precision_horizontal <= 5 else 'danger'
            color_v = 'success' if obj.precision_vertical <= 1 else 'warning' if obj.precision_vertical <= 3 else 'danger'
            return format_html(
                '''
                <div>
                    <span class="badge badge-{}">H: ±{}cm</span>
                    <span class="badge badge-{}">V: ±{}cm</span>
                </div>
                ''',
                color_h, obj.precision_horizontal,
                color_v, obj.precision_vertical
            )
        return mark_safe('<span class="text-muted">No especificada</span>')

    @display(description="Validado", ordering="validado")
    def validado_badge(self, obj):
        if obj.validado:
            return mark_safe('<span class="badge badge-success">✓ Validado</span>')
        return mark_safe('<span class="badge badge-warning">Pendiente</span>')

    @display(description="Fecha", ordering="fecha_medicion")
    def fecha_medicion_display(self, obj):
        return format_html(
            '{}',
            obj.fecha_medicion.strftime('%d/%m/%Y %H:%M')
        )

    @display(description="Detalle de Coordenadas")
    def coordenadas_detalle(self, obj):
        return format_html(
            '''
            <table style="width: 100%; border-collapse: collapse;">
                <tr style="background: #f8f9fa;">
                    <th style="padding: 0.5rem; text-align: left;">Sistema</th>
                    <th style="padding: 0.5rem; text-align: left;">Coordenadas</th>
                </tr>
                <tr>
                    <td style="padding: 0.5rem;"><strong>WGS84</strong></td>
                    <td style="padding: 0.5rem; font-family: monospace;">
                        Lat: {:.6f}°<br/>
                        Lon: {:.6f}°<br/>
                        Elev: {:.3f}m
                    </td>
                </tr>
                <tr style="background: #f8f9fa;">
                    <td style="padding: 0.5rem;"><strong>Precisión</strong></td>
                    <td style="padding: 0.5rem;">
                        Horizontal: ±{}cm<br/>
                        Vertical: ±{}cm
                    </td>
                </tr>
            </table>
            ''',
            obj.latitud, obj.longitud, obj.elevacion,
            obj.precision_horizontal or 'N/A',
            obj.precision_vertical or 'N/A'
        )

    @display(description="Ubicación en Mapa")
    def mapa_punto(self, obj):
        return format_html(
            '''
            <div id="map-punto-{}" style="height: 300px; border-radius: 8px;"></div>
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
            <script>
                var map = L.map('map-punto-{}').setView([{}, {}], 17);
                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(map);
                L.marker([{}, {}]).addTo(map)
                    .bindPopup('<b>{}</b><br/>Tipo: {}<br/>Elev: {}m');
            </script>
            ''',
            obj.pk, obj.pk,
            obj.latitud, obj.longitud,
            obj.latitud, obj.longitud,
            obj.numero_punto, obj.get_tipo_display(), obj.elevacion
        )

    @admin.action(description="✓ Validar puntos seleccionados")
    def validar_puntos(self, request, queryset):
        queryset.update(
            validado=True,
            validado_por=request.user,
            fecha_validacion=timezone.now()
        )
        self.message_user(request, f'{queryset.count()} puntos validados', 'success')


# ============================================
# VOLUMEN TERRACERIA ADMIN
# ============================================

@admin.register(VolumenTerraceria)
class VolumenTerraceriaAdmin(ModelAdmin):
    list_display = [
        'nombre',
        'proyecto_link',
        'metodo_badge',
        'area_display',
        'volumenes_display',
        'balance_badge',
        'fecha_calculo_display',
    ]

    list_filter = [
        ('metodo_calculo', ChoicesDropdownFilter),
        ('fecha_calculo', RangeDateFilter),
        ('proyecto', admin.RelatedOnlyFieldListFilter),
    ]

    search_fields = ['nombre', 'descripcion', 'proyecto__codigo']

    readonly_fields = ['fecha_calculo', 'grafica_volumenes', 'resumen_calculo']

    fieldsets = (
        ('Información General', {
            'fields': ('proyecto', 'nombre', 'descripcion', 'metodo_calculo'),
        }),
        ('Resultados', {
            'fields': (
                'area_m2',
                ('volumen_corte_m3', 'volumen_relleno_m3'),
                'volumen_neto_m3',
                'grafica_volumenes',
                'resumen_calculo',
            ),
        }),
        ('Datos del Levantamiento', {
            'fields': (
                'archivo_levantamiento',
                'calculado_por',
                'fecha_calculo',
            ),
        }),
    )

    @display(description="Proyecto")
    def proyecto_link(self, obj):
        url = reverse('admin:sisgestionobras_proyecto_change', args=[obj.proyecto.pk])
        return format_html('<a href="{}">{}</a>', url, obj.proyecto.codigo)

    @display(description="Método", ordering="metodo_calculo")
    def metodo_badge(self, obj):
        icons = {
            'SECCIONES': '📊',
            'GRID': '⊞',
            'TIN': '▲',
            'CURVAS': '〰️',
        }
        return format_html(
            '{} {}',
            icons.get(obj.metodo_calculo, '📐'),
            obj.get_metodo_calculo_display()
        )

    @display(description="Área", ordering="area_m2")
    def area_display(self, obj):
        return format_html(
            '<strong>{}</strong> m²',
            f'{obj.area_m2:,.0f}'
        )

    @display(description="Volúmenes")
    def volumenes_display(self, obj):
        return format_html(
            '''
            <div style="font-size: 0.875rem;">
                <div style="color: #dc2626;">⬇️ Corte: {} m³</div>
                <div style="color: #2563eb;">⬆️ Relleno: {} m³</div>
            </div>
            ''',
            f'{obj.volumen_corte_m3:,.0f}',
            f'{obj.volumen_relleno_m3:,.0f}'
        )

    @display(description="Balance", ordering="volumen_neto_m3")
    def balance_badge(self, obj):
        neto = obj.volumen_neto_m3
        if abs(neto) < 100:
            return mark_safe(
                '<span class="badge badge-success">✓ Compensado</span>'
            )
        elif neto > 0:
            return format_html(
                '<span class="badge badge-danger">⬇️ Corte +{} m³</span>',
                f'{neto:,.0f}'
            )
        else:
            return format_html(
                '<span class="badge badge-primary">⬆️ Relleno {} m³</span>',
                f'{abs(neto):,.0f}'
            )

    @display(description="Fecha", ordering="fecha_calculo")
    def fecha_calculo_display(self, obj):
        return obj.fecha_calculo.strftime('%d/%m/%Y %H:%M')

    @display(description="Gráfica de Volúmenes")
    def grafica_volumenes(self, obj):
        corte = obj.volumen_corte_m3
        relleno = obj.volumen_relleno_m3
        total = corte + relleno

        porc_corte = (corte / total * 100) if total > 0 else 0
        porc_relleno = (relleno / total * 100) if total > 0 else 0

        return format_html(
            '''
            <div style="margin: 1rem 0;width: 100%;">
                <div style="display: flex; height: 40px; border-radius: 8px; overflow: hidden;width: 100%;">
                    <div style="background: #dc2626;width: 100%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">
                        {}%
                    </div>
                    <div style="background: #2563eb;width: 100%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">
                        {}%
                    </div>
                </div>
                <div style="display: flex; justify-content: space-between; margin-top: 0.5rem; font-size: 0.875rem;">
                    <div>🔴 Corte: {} m³</div>
                    <div>🔵 Relleno: {} m³</div>
                </div>
            </div>
            ''',
            f'{porc_corte:.0f}', f'{porc_corte:.0f}',
            f'{porc_relleno:.0f}', f'{porc_relleno:.0f}',
            f'{corte:.0f}', f'{relleno:.0f}'
        )

    @display(description="Resumen del Cálculo")
    def resumen_calculo(self, obj):
        neto = obj.volumen_neto_m3
        tipo_balance = 'Compensado' if abs(neto) < 100 else ('Corte' if neto > 0 else 'Relleno')

        return format_html(
            '''
            <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px;">
                <h4 style="margin-top: 0;">Resumen Ejecutivo</h4>
                <table style="width: 100%;">
                    <tr>
                        <td><strong>Área procesada:</strong></td>
                        <td>{} m²</td>
                    </tr>
                    <tr>
                        <td><strong>Volumen de corte:</strong></td>
                        <td style="color: #dc2626;">{} m³</td>
                    </tr>
                    <tr>
                        <td><strong>Volumen de relleno:</strong></td>
                        <td style="color: #2563eb;">{} m³</td>
                    </tr>
                    <tr>
                        <td><strong>Volumen neto:</strong></td>
                        <td><strong>{} m³</strong></td>
                    </tr>
                    <tr>
                        <td><strong>Tipo de balance:</strong></td>
                        <td><span class="badge badge-info">{}</span></td>
                    </tr>
                    <tr>
                        <td><strong>Método de cálculo:</strong></td>
                        <td>{}</td>
                    </tr>
                </table>
            </div>
            ''',
            f'{obj.area_m2:,.0f}',
            f'{obj.volumen_corte_m3:,.2f}',
            f'{obj.volumen_relleno_m3:,.2f}',
            f'{abs(neto):,.2f}',
            tipo_balance,
            obj.get_metodo_calculo_display()
        )


class ObrasCivilesAdminSite(AdminSite):
    site_header = "🏗️ Sistema de Gestión de Obras Civiles"
    site_title = "Gestión de Obras"
    index_title = "Panel de Control"

    def index(self, request, extra_context=None):
        extra_context = extra_context or {}

        # Estadísticas generales
        total_proyectos = Proyecto.objects.count()
        proyectos_activos = Proyecto.objects.filter(estado='EJECUCION').count()
        total_elementos = ElementoConstructivo.objects.count()
        elementos_terminados = ElementoConstructivo.objects.filter(estado='TERMINADO').count()

        # Proyectos recientes
        proyectos_recientes = Proyecto.objects.order_by('-created_at')[:5]

        # Reportes de la última semana
        hace_semana = timezone.now() - timedelta(days=7)
        reportes_semana = ReporteAvance.objects.filter(fecha__gte=hace_semana).count()

        extra_context.update({
            'total_proyectos': total_proyectos,
            'proyectos_activos': proyectos_activos,
            'total_elementos': total_elementos,
            'elementos_terminados': elementos_terminados,
            'proyectos_recientes': proyectos_recientes,
            'reportes_semana': reportes_semana,
        })

        return super().index(request, extra_context)


admin_site = ObrasCivilesAdminSite(name='admin')
