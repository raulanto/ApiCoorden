from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProyectoViewSet,
    ElementoConstructivoViewSet,
    PuntoControlViewSet,
    CuadrillaViewSet,
    ReporteAvanceViewSet,
    VolumenTerraceriaViewSet
)

router = DefaultRouter()
router.register(r'proyectos', ProyectoViewSet, basename='proyecto')
router.register(r'elementos', ElementoConstructivoViewSet, basename='elemento')
router.register(r'puntos-control', PuntoControlViewSet, basename='punto-control')
router.register(r'cuadrillas', CuadrillaViewSet, basename='cuadrilla')
router.register(r'reportes', ReporteAvanceViewSet, basename='reporte')
router.register(r'volumenes', VolumenTerraceriaViewSet, basename='volumen')

urlpatterns = [
    path('', include(router.urls)),
]
