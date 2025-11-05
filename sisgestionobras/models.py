from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid


class Proyecto(models.Model):
    """Proyecto de construcción principal"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=200)
    codigo = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True)
    cliente = models.CharField(max_length=200)

    # Configuración de coordenadas
    SISTEMAS_COORDENADAS = [
        ('WGS84', 'WGS84 (GPS)'),
        ('UTM', 'Universal Transverse Mercator'),
        ('LOCAL', 'Sistema Local'),
    ]
    sistema_coordenadas = models.CharField(
        max_length=10,
        choices=SISTEMAS_COORDENADAS,
        default='UTM'
    )
    zona_utm = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(60)]
    )
    hemisferio = models.CharField(
        max_length=1,
        choices=[('N', 'Norte'), ('S', 'Sur')],
        null=True,
        blank=True
    )

    # Punto de referencia del proyecto (BenchMark)
    lat_referencia = models.FloatField(help_text="Latitud del punto de referencia")
    lon_referencia = models.FloatField(help_text="Longitud del punto de referencia")
    elevacion_referencia = models.FloatField(
        default=0,
        help_text="Elevación sobre nivel del mar (m)"
    )

    # Administración
    director_obra = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='proyectos_dirigidos'
    )
    residente_obra = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='proyectos_residencia'
    )

    # Fechas
    fecha_inicio = models.DateField()
    fecha_fin_estimada = models.DateField()
    fecha_fin_real = models.DateField(null=True, blank=True)

    # Estado
    ESTADOS = [
        ('PLAN', 'Planificación'),
        ('EJECUCION', 'En Ejecución'),
        ('PAUSADO', 'Pausado'),
        ('FINALIZADO', 'Finalizado'),
    ]
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PLAN')

    # Presupuesto
    presupuesto_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Proyecto"
        verbose_name_plural = "Proyectos"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class ElementoConstructivo(models.Model):
    """
    Elementos específicos de la obra: zapatas, columnas, muros, etc.
    Cada elemento tiene coordenadas precisas
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='elementos')

    # Identificación
    codigo = models.CharField(max_length=50)
    nombre = models.CharField(max_length=200)

    TIPOS_ELEMENTO = [
        ('ZAPATA', 'Zapata'),
        ('COLUMNA', 'Columna'),
        ('TRABE', 'Trabe/Viga'),
        ('MURO', 'Muro'),
        ('LOSA', 'Losa'),
        ('CIMENTACION', 'Cimentación'),
        ('PAVIMENTO', 'Pavimento'),
        ('TERRACERIA', 'Terracería'),
        ('DRENAJE', 'Drenaje'),
        ('OTRO', 'Otro'),
    ]
    tipo = models.CharField(max_length=20, choices=TIPOS_ELEMENTO)

    # Coordenadas del elemento (centro o punto de control)
    latitud = models.FloatField()
    longitud = models.FloatField()
    elevacion = models.FloatField(help_text="Elevación en metros")

    # Coordenadas UTM (calculadas automáticamente)
    utm_este = models.FloatField(null=True, blank=True)
    utm_norte = models.FloatField(null=True, blank=True)
    utm_zona = models.IntegerField(null=True, blank=True)

    # Geometría (para elementos con área)
    area_proyecto = models.FloatField(
        null=True,
        blank=True,
        help_text="Área en m²"
    )
    volumen_proyecto = models.FloatField(
        null=True,
        blank=True,
        help_text="Volumen en m³"
    )
    longitud_proyecto = models.FloatField(
        null=True,
        blank=True,
        help_text="Longitud en m"
    )

    # Control de avance
    porcentaje_avance = models.FloatField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    ESTADOS_ELEMENTO = [
        ('PENDIENTE', 'Pendiente'),
        ('REPLANTEO', 'En Replanteo'),
        ('EXCAVACION', 'Excavación'),
        ('CIMBRADO', 'Cimbrado'),
        ('ARMADO', 'Armado de Acero'),
        ('COLADO', 'Colado'),
        ('TERMINADO', 'Terminado'),
    ]
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS_ELEMENTO,
        default='PENDIENTE'
    )

    # Responsable
    responsable = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='elementos_responsable'
    )

    # Fechas
    fecha_inicio_programada = models.DateField(null=True, blank=True)
    fecha_inicio_real = models.DateField(null=True, blank=True)
    fecha_fin_programada = models.DateField(null=True, blank=True)
    fecha_fin_real = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Elemento Constructivo"
        verbose_name_plural = "Elementos Constructivos"
        unique_together = ['proyecto', 'codigo']
        ordering = ['codigo']

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class PuntoControl(models.Model):
    """
    Puntos de control topográfico y levantamientos
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='puntos_control')
    elemento = models.ForeignKey(
        ElementoConstructivo,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='puntos_control'
    )

    # Identificación
    numero_punto = models.CharField(max_length=50)
    descripcion = models.TextField(blank=True)

    TIPOS_PUNTO = [
        ('BENCHMARK', 'Banco de Nivel'),
        ('REPLANTEO', 'Punto de Replanteo'),
        ('VERIFICACION', 'Verificación'),
        ('CONTROL', 'Control de Calidad'),
        ('LEVANTAMIENTO', 'Levantamiento'),
    ]
    tipo = models.CharField(max_length=20, choices=TIPOS_PUNTO)

    # Coordenadas medidas
    latitud = models.FloatField()
    longitud = models.FloatField()
    elevacion = models.FloatField()

    # Precisión de la medición
    precision_horizontal = models.FloatField(
        help_text="Precisión horizontal en cm",
        null=True,
        blank=True
    )
    precision_vertical = models.FloatField(
        help_text="Precisión vertical en cm",
        null=True,
        blank=True
    )

    # Equipo utilizado
    EQUIPOS = [
        ('GPS_DIFERENCIAL', 'GPS Diferencial'),
        ('GPS_RTK', 'GPS RTK'),
        ('ESTACION_TOTAL', 'Estación Total'),
        ('NIVEL', 'Nivel Óptico'),
        ('GPS_MOVIL', 'GPS Móvil'),
    ]
    equipo_medicion = models.CharField(max_length=30, choices=EQUIPOS)

    # Responsable de la medición
    topografo = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    fecha_medicion = models.DateTimeField(auto_now_add=True)

    # Validación
    validado = models.BooleanField(default=False)
    validado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='puntos_validados'
    )
    fecha_validacion = models.DateTimeField(null=True, blank=True)

    observaciones = models.TextField(blank=True)

    class Meta:
        verbose_name = "Punto de Control"
        verbose_name_plural = "Puntos de Control"
        ordering = ['-fecha_medicion']

    def __str__(self):
        return f"Punto {self.numero_punto} - {self.tipo}"


class Cuadrilla(models.Model):
    """Equipos de trabajo en campo"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='cuadrillas')

    nombre = models.CharField(max_length=100)
    jefe_cuadrilla = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    # Ubicación actual en tiempo real
    latitud_actual = models.FloatField(null=True, blank=True)
    longitud_actual = models.FloatField(null=True, blank=True)
    ultima_actualizacion = models.DateTimeField(null=True, blank=True)

    # Actividad actual
    elemento_actual = models.ForeignKey(
        ElementoConstructivo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cuadrillas_trabajando'
    )

    activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Cuadrilla"
        verbose_name_plural = "Cuadrillas"

    def __str__(self):
        return f"{self.nombre} - {self.proyecto.codigo}"


class ReporteAvance(models.Model):
    """Reportes diarios de avance con evidencia fotográfica"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    elemento = models.ForeignKey(
        ElementoConstructivo,
        on_delete=models.CASCADE,
        related_name='reportes'
    )
    cuadrilla = models.ForeignKey(
        Cuadrilla,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reportes'
    )

    # Información del reporte
    fecha = models.DateField(auto_now_add=True)
    hora = models.TimeField(auto_now_add=True)
    reportado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    # Ubicación donde se tomó el reporte
    latitud = models.FloatField()
    longitud = models.FloatField()

    # Mediciones
    avance_cantidad = models.FloatField(
        help_text="Cantidad ejecutada en la unidad del concepto"
    )
    avance_porcentaje = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    # Evidencia
    foto = models.ImageField(upload_to='reportes_avance/', null=True, blank=True)
    descripcion = models.TextField()

    # Recursos utilizados
    materiales_utilizados = models.TextField(blank=True)
    personal_asignado = models.IntegerField(default=0)
    horas_trabajadas = models.FloatField(default=0)

    # Validación
    validado = models.BooleanField(default=False)
    validado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reportes_validados'
    )

    class Meta:
        verbose_name = "Reporte de Avance"
        verbose_name_plural = "Reportes de Avance"
        ordering = ['-fecha', '-hora']

    def __str__(self):
        return f"Reporte {self.elemento.codigo} - {self.fecha}"


class VolumenTerraceria(models.Model):
    """Cálculo de volúmenes de corte y relleno"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='volumenes')

    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)

    # Área del cálculo (polígono definido por puntos)
    # En producción usarías GeoDjango con PolygonField
    area_m2 = models.FloatField()

    # Volúmenes calculados
    volumen_corte_m3 = models.FloatField(default=0)
    volumen_relleno_m3 = models.FloatField(default=0)
    volumen_neto_m3 = models.FloatField(default=0)  # corte - relleno

    # Método de cálculo
    METODOS = [
        ('SECCIONES', 'Áreas de Secciones'),
        ('GRID', 'Retícula (Grid)'),
        ('TIN', 'Triangulación (TIN)'),
        ('CURVAS', 'Curvas de Nivel'),
    ]
    metodo_calculo = models.CharField(max_length=20, choices=METODOS)

    # Fechas
    fecha_calculo = models.DateTimeField(auto_now_add=True)
    calculado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    # Datos del levantamiento
    archivo_levantamiento = models.FileField(
        upload_to='levantamientos/',
        null=True,
        blank=True,
        help_text="Archivo CSV con coordenadas del levantamiento"
    )

    class Meta:
        verbose_name = "Volumen de Terracería"
        verbose_name_plural = "Volúmenes de Terracería"
        ordering = ['-fecha_calculo']

    def __str__(self):
        return f"{self.nombre} - {self.fecha_calculo.date()}"
