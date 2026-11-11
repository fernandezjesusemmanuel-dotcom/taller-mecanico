from django.urls import path, re_path
from django.conf import settings
from django.views.static import serve
from . import views

urlpatterns = [
    path('', views.pantalla_3d, name='pantalla_3d'),
    path('api/estado/', views.api_estado, name='api_estado'),
    path('api/presupuesto/', views.api_responder_presupuesto, name='api_responder_presupuesto'),
    path('api/notificar/', views.api_suscribir_aviso, name='api_suscribir_aviso'),
    path('panel-taller/', views.dashboard_mecanico, name='dashboard_mecanico'),
    path('panel-taller/estado/<int:orden_id>/', views.cambiar_estado_orden, name='cambiar_estado_orden'),
    path('panel-taller/exportar/<int:orden_id>/', views.exportar_orden_pdf, name='exportar_orden_pdf'),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]