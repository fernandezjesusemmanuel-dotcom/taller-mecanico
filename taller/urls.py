from django.urls import path
from . import views

urlpatterns = [
    path('', views.pantalla_3d, name='pantalla_3d'),
    path('api/estado/', views.api_estado, name='api_estado'),
    path('panel-taller/', views.dashboard_mecanico, name='dashboard_mecanico'),
    # Ruta para descargar el PDF
    path('panel-taller/exportar/<int:orden_id>/', views.exportar_orden_pdf, name='exportar_orden_pdf'),
]