from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Sum
from django.contrib.admin.views.decorators import staff_member_required
from django.template.loader import render_to_string
import weasyprint

from .models import Vehiculo, OrdenReparacion, Repuesto

@staff_member_required
def dashboard_mecanico(request):
    hoy = timezone.now().date()
    
    # 1. Métricas Rápidas
    ordenes_hoy = OrdenReparacion.objects.filter(fecha_ingreso__date=hoy).count()
    ordenes_proceso = OrdenReparacion.objects.exclude(estado__in=['LISTO', 'ENTREGADO']).count()
    
    facturacion_mes = OrdenReparacion.objects.filter(
        fecha_ingreso__month=hoy.month
    ).aggregate(total=Sum('total_estimado'))['total'] or 0
    
    # 2. Semáforo de Insumos Críticos
    repuestos = Repuesto.objects.filter(activo=True)
    repuestos_criticos = [r for r in repuestos if r.esta_bajo_stock()]
    
    # 3. Agenda de Trabajo Activa
    agenda = OrdenReparacion.objects.exclude(estado='ENTREGADO').order_by('-fecha_ingreso')[:15]
    
    return render(request, 'taller/admin_dashboard.html', {
        'ordenes_hoy': ordenes_hoy,
        'ordenes_proceso': ordenes_proceso,
        'facturacion_mes': facturacion_mes,
        'repuestos_criticos': repuestos_criticos,
        'agenda': agenda,
    })


@staff_member_required
def exportar_orden_pdf(request, orden_id):
    # Obtener la orden de reparación
    orden = OrdenReparacion.objects.get(id=orden_id)
    
    # Renderizar la plantilla HTML a string con los datos de la orden
    html_string = render_to_string('taller/orden_pdf.html', {'orden': orden})
    
    # Generar el PDF
    html = weasyprint.HTML(string=html_string)
    pdf = html.write_pdf()
    
    # Configurar la respuesta HTTP
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="orden_{orden.id}_{orden.vehiculo.patente}.pdf"'
    return response


def pantalla_3d(request):
    # Por ahora solo devuelve la vista HTML
    return render(request, 'taller/consulta.html')


def api_estado(request):
    # Estructura base para la API REST que alimentará el modelo 3D
    patente = request.GET.get('patente', '').strip().upper()
    
    if not patente:
        return JsonResponse({'error': 'Patente no provista'}, status=400)
        
    try:
        vehiculo = Vehiculo.objects.get(patente=patente)
        orden = OrdenReparacion.objects.filter(vehiculo=vehiculo).first()
        
        if not orden:
            return JsonResponse({'error': 'Sin órdenes activas'}, status=404)
            
        data = {
            'vehiculo': f"{vehiculo.marca} {vehiculo.modelo}",
            'fase': 1,
            'costo': 0,
            'horas': 0,
            'diagnostico': 'En revisión preliminar',
            'piezas': [],
            'zonas': []
        }
        return JsonResponse(data)
        
    except Vehiculo.DoesNotExist:
        return JsonResponse({'error': 'Vehículo no encontrado'}, status=404)