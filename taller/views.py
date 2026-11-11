import json
import urllib.parse
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Sum
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
import weasyprint

from .models import Vehiculo, OrdenReparacion, Repuesto

TALLER_WHATSAPP = "5492615962434"


def _clasificar_segmento(marca, modelo):
    nombre = f"{marca} {modelo}".lower()
    if any(k in nombre for k in ['compact', '206', '207', '208', 'gol', 'palio', 'clio', 'fiesta', 'hatch']):
        return 'hatchback'
    elif any(k in nombre for k in ['hilux', 'ranger', 'amarok', 'toro', 'saveiro', 'pickup', 'camioneta']):
        return 'pickup'
    elif any(k in nombre for k in ['suv', 'ecosport', 'duster', 'tracker', 'kangoo', 'partner']):
        return 'suv'
    return 'sedan'


@staff_member_required
def dashboard_mecanico(request):
    hoy = timezone.now().date()
    
    # 1. Métricas Rápidas
    ordenes_hoy = OrdenReparacion.objects.filter(fecha_ingreso__date=hoy).count()
    ordenes_proceso = OrdenReparacion.objects.exclude(estado__in=['LISTO', 'ENTREGADO']).count()
    
    ordenes_mes_qs = OrdenReparacion.objects.filter(fecha_ingreso__month=hoy.month)
    facturacion_mes = ordenes_mes_qs.aggregate(total=Sum('total_estimado'))['total'] or 0
    total_ordenes_mes = ordenes_mes_qs.count()
    ticket_promedio = round(float(facturacion_mes) / total_ordenes_mes, 0) if total_ordenes_mes > 0 else 0
    
    # 2. Semáforo de Insumos Críticos
    repuestos = Repuesto.objects.filter(activo=True)
    repuestos_criticos = [r for r in repuestos if r.esta_bajo_stock()]
    
    # 3. Agenda de Trabajo Activa y Estadísticas Avanzadas (Punto 4)
    todas_activas = OrdenReparacion.objects.exclude(estado='ENTREGADO').order_by('-fecha_ingreso')
    agenda = todas_activas[:15]
    base_url = request.build_absolute_uri('/')[:-1]

    conteo_fases = {
        'RECIBIDO': 0,
        'DIAGNOSTICO': 0,
        'REPUESTOS': 0,
        'EN_REPARACION': 0,
        'LISTO': 0,
    }
    conteo_tipos = {
        'Hatchback / Compacto': 0,
        'Sedán': 0,
        'Pick-up': 0,
        'SUV / Utilitario': 0,
    }
    aprobados_count = 0

    for o in todas_activas:
        est = str(o.estado).upper()
        if est == 'REPARACION':
            est = 'EN_REPARACION'
        if est in conteo_fases:
            conteo_fases[est] += 1

        seg = _clasificar_segmento(o.vehiculo.marca, o.vehiculo.modelo)
        if seg == 'hatchback':
            conteo_tipos['Hatchback / Compacto'] += 1
        elif seg == 'pickup':
            conteo_tipos['Pick-up'] += 1
        elif seg == 'suv':
            conteo_tipos['SUV / Utilitario'] += 1
        else:
            conteo_tipos['Sedán'] += 1

        diag_txt = getattr(o, 'diagnostico', '') or ''
        if '[PRESUPUESTO APROBADO]' in diag_txt or est in ('EN_REPARACION', 'LISTO'):
            aprobados_count += 1

    total_activas_count = todas_activas.count()
    tasa_aprobacion = round((aprobados_count / total_activas_count) * 100) if total_activas_count > 0 else 0

    for orden in agenda:
        estado_legible = orden.get_estado_display() if hasattr(orden, 'get_estado_display') else orden.estado
        diag_actual = getattr(orden, 'diagnostico', '') or ''
        
        if '[PRESUPUESTO APROBADO]' in diag_actual or str(orden.estado).upper() in ('EN_REPARACION', 'REPARACION', 'LISTO'):
            orden.estado_presupuesto = 'APROBADO'
        elif '[REVISIÓN SOLICITADA]' in diag_actual:
            orden.estado_presupuesto = 'RECHAZADO'
        else:
            orden.estado_presupuesto = 'PENDIENTE'

        orden.solicita_aviso = '[AVISO ACTIVO]' in diag_actual

        mensaje_wa = (
            f"🔧 *Taller Mecánico - Actualización de Estado*\n\n"
            f"Hola {orden.vehiculo.dueño_nombre}, te informamos que tu vehículo "
            f"*{orden.vehiculo.marca} {orden.vehiculo.modelo}* (Patente *{orden.vehiculo.patente}*) "
            f"pasó a la fase: *{estado_legible}*.\n"
            f"💰 Presupuesto estimado: ${orden.total_estimado}\n\n"
            f"Podés ver el seguimiento 3D en vivo y aprobar el presupuesto acá:\n"
            f"{base_url}/?patente={urllib.parse.quote(orden.vehiculo.patente)}"
        )
        telefono_cliente = getattr(orden.vehiculo, 'dueño_telefono', '') or ''
        telefono_limpio = ''.join(filter(str.isdigit, str(telefono_cliente)))
        if telefono_limpio:
            orden.whatsapp_url = f"https://wa.me/{telefono_limpio}?text={urllib.parse.quote(mensaje_wa)}"
        else:
            orden.whatsapp_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(mensaje_wa)}"

    return render(request, 'taller/admin_dashboard.html', {
        'ordenes_hoy': ordenes_hoy,
        'ordenes_proceso': ordenes_proceso,
        'facturacion_mes': facturacion_mes,
        'ticket_promedio': int(ticket_promedio),
        'tasa_aprobacion': tasa_aprobacion,
        'repuestos_criticos': repuestos_criticos,
        'agenda': agenda,
        'fases_json': json.dumps(list(conteo_fases.values())),
        'tipos_labels_json': json.dumps(list(conteo_tipos.keys())),
        'tipos_values_json': json.dumps(list(conteo_tipos.values())),
    })


@staff_member_required
@require_POST
def cambiar_estado_orden(request, orden_id):
    orden = get_object_or_404(OrdenReparacion, id=orden_id)
    nuevo_estado = request.POST.get('estado', '').strip()
    if nuevo_estado:
        orden.estado = nuevo_estado
        orden.save()

        email_cliente = getattr(orden.vehiculo, 'dueño_email', None)
        if email_cliente:
            estado_legible = orden.get_estado_display() if hasattr(orden, 'get_estado_display') else orden.estado
            try:
                send_mail(
                    subject=f"Actualización de tu vehículo {orden.vehiculo.patente} - {estado_legible}",
                    message=(
                        f"Hola {orden.vehiculo.dueño_nombre},\n\n"
                        f"Tu vehículo {orden.vehiculo.marca} {orden.vehiculo.modelo} ({orden.vehiculo.patente}) "
                        f"ha cambiado al estado: {estado_legible}.\n"
                        f"Total estimado: ${orden.total_estimado}\n\n"
                        f"Ingresá a nuestra plataforma para ver el estado en tiempo real."
                    ),
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@taller.com'),
                    recipient_list=[email_cliente],
                    fail_silently=True,
                )
            except Exception:
                pass

    return redirect('dashboard_mecanico')


@staff_member_required
def exportar_orden_pdf(request, orden_id):
    orden = OrdenReparacion.objects.get(id=orden_id)
    html_string = render_to_string('taller/orden_pdf.html', {'orden': orden})
    html = weasyprint.HTML(string=html_string)
    pdf = html.write_pdf()
    
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="orden_{orden.id}_{orden.vehiculo.patente}.pdf"'
    return response


def pantalla_3d(request):
    return render(request, 'taller/consulta.html')


def api_estado(request):
    patente_input = request.GET.get('patente', '').replace(' ', '').replace('-', '').strip().upper()
    
    if not patente_input:
        return JsonResponse({'detail': 'Patente no provista'}, status=400)
        
    vehiculo = None
    for v in Vehiculo.objects.all():
        patente_limpia = v.patente.replace(' ', '').replace('-', '').strip().upper()
        if patente_limpia == patente_input:
            vehiculo = v
            break
            
    if not vehiculo:
        return JsonResponse({'detail': 'Vehículo no encontrado'}, status=404)
        
    orden = OrdenReparacion.objects.filter(vehiculo=vehiculo).exclude(estado='ENTREGADO').order_by('-fecha_ingreso').first()
    
    if not orden:
        return JsonResponse({'detail': 'Vehículo sin órdenes activas'}, status=404)

    mapa_fases = {
        'RECIBIDO': 1,
        'DIAGNOSTICO': 2,
        'PRESUPUESTO': 2,
        'REPUESTOS': 3,
        'REPARACION': 4,
        'EN_REPARACION': 4,
        'LISTO': 5,
    }
    estado_upper = str(orden.estado).upper()
    fase_actual = mapa_fases.get(estado_upper, 1)

    piezas = []
    if hasattr(orden, 'detalles'):
        piezas = [f"{d.cantidad}x {d.repuesto.nombre}" for d in orden.detalles.all()]
    elif hasattr(orden, 'detalleorden_set'):
        piezas = [f"{d.cantidad}x {d.repuesto.nombre}" for d in orden.detalleorden_set.all()]

    tipo_3d = _clasificar_segmento(vehiculo.marca, vehiculo.modelo)

    diagnostico_texto = getattr(orden, 'diagnostico', '') or 'En revisión preliminar por el equipo técnico.'
    texto_analisis = f"{diagnostico_texto} {' '.join(piezas)}".lower()
    estado_legible = orden.get_estado_display() if hasattr(orden, 'get_estado_display') else orden.estado

    todo_listo = (fase_actual == 5)
    zonas = [
        {
            'id': 'motor',
            'nombre': 'Motor y Distribución',
            'estado': 'ok' if todo_listo else 'work',
            'nota': f"Motor · {estado_legible}",
            'detalle': 'Inspección de compresión, correa de distribución, fluidos y estanqueidad térmica.'
        },
        {
            'id': 'frenos',
            'nombre': 'Frenos y Discos ABS',
            'estado': 'ok' if (todo_listo or (fase_actual >= 4 and 'freno' not in texto_analisis and 'pastilla' not in texto_analisis)) else 'work',
            'nota': 'Frenos ABS · Pastillas y Discos',
            'detalle': 'Control de espesor de pastillas delanteras, discos ventilados y circuito hidráulico.'
        },
        {
            'id': 'suspension',
            'nombre': 'Suspensión y Tren Delantero',
            'estado': 'ok' if (todo_listo or (fase_actual >= 3 and 'amortiguador' not in texto_analisis and 'suspensi' not in texto_analisis and 'tren' not in texto_analisis)) else 'work',
            'nota': 'Suspensión · Amortiguadores y Bujes',
            'detalle': 'Verificación de amortiguadores, extremos de dirección, rótulas y alineación.'
        },
        {
            'id': 'electrico',
            'nombre': 'Electrónica OBC y Sensores',
            'estado': 'ok' if (todo_listo or fase_actual >= 3) else 'work',
            'nota': 'Escaneo OBC · ECU y Sensores',
            'detalle': 'Lectura de códigos de falla por puerto OBD-II, sensores de inyección y telemetría.'
        },
        {
            'id': 'bateria',
            'nombre': 'Batería y Alternador',
            'estado': 'ok' if (todo_listo or 'bateria' not in texto_analisis) else 'work',
            'nota': 'Sistema de Carga · 12.6V Nominal',
            'detalle': 'Prueba de caída de tensión en arranque y carga continua del alternador.'
        },
        {
            'id': 'transmision',
            'nombre': 'Transmisión y Embrague',
            'estado': 'ok' if (todo_listo or ('embrague' not in texto_analisis and 'caja' not in texto_analisis)) else 'work',
            'nota': 'Transmisión · Caja y Semiejes',
            'detalle': 'Revisión de acople de embrague, retenes de caja y guardapolvos de homocinética.'
        },
        {
            'id': 'escape',
            'nombre': 'Escape y Catalizador',
            'estado': 'ok' if (todo_listo or 'escape' not in texto_analisis) else 'work',
            'nota': 'Gases y Escape · Sonda Lambda',
            'detalle': 'Control de emisiones, fijaciones del silenciador trasero y estanqueidad de múltiple.'
        },
    ]

    if '[PRESUPUESTO APROBADO]' in diagnostico_texto or fase_actual >= 4:
        estado_presupuesto = 'APROBADO'
    elif '[REVISIÓN SOLICITADA]' in diagnostico_texto:
        estado_presupuesto = 'RECHAZADO'
    else:
        estado_presupuesto = 'PENDIENTE'

    aviso_activo = '[AVISO ACTIVO]' in diagnostico_texto

    mensaje_taller = (
        f"Hola Taller, consulto por mi vehículo {vehiculo.marca} {vehiculo.modelo} "
        f"(Patente {vehiculo.patente}) - Orden #{orden.id}. "
        f"Quisiera recibir notificaciones cuando esté listo."
    )
    whatsapp_taller_url = f"https://wa.me/{TALLER_WHATSAPP}?text={urllib.parse.quote(mensaje_taller)}"

    data = {
        'orden_id': orden.id,
        'patente': vehiculo.patente,
        'vehiculo': f"{vehiculo.marca} {vehiculo.modelo}",
        'tipo_3d': tipo_3d,
        'modelo_glb': getattr(vehiculo, 'modelo_3d_url', None),
        'fase': fase_actual,
        'costo': float(getattr(orden, 'total_estimado', 0) or 0),
        'horas': float(getattr(orden, 'horas_estimadas', 2.5) or 2.5),
        'diagnostico': diagnostico_texto,
        'estado_presupuesto': estado_presupuesto,
        'aviso_activo': aviso_activo,
        'whatsapp_taller_url': whatsapp_taller_url,
        'piezas': piezas,
        'zonas': zonas,
    }
    return JsonResponse(data)


@csrf_exempt
@require_POST
def api_responder_presupuesto(request):
    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'detail': 'Formato JSON inválido'}, status=400)

    orden_id = body.get('orden_id')
    accion = body.get('accion')

    if not orden_id or accion not in ('aprobar', 'rechazar'):
        return JsonResponse({'detail': 'Parámetros incompletos'}, status=400)

    try:
        orden = OrdenReparacion.objects.get(id=orden_id)
    except OrdenReparacion.DoesNotExist:
        return JsonResponse({'detail': 'Orden no encontrada'}, status=404)

    diag_actual = getattr(orden, 'diagnostico', '') or ''
    for tag in ['[PRESUPUESTO APROBADO]', '[REVISIÓN SOLICITADA]']:
        diag_actual = diag_actual.replace(tag, '').strip()

    if accion == 'aprobar':
        estados_disponibles = [c[0] for c in OrdenReparacion._meta.get_field('estado').choices]
        if 'EN_REPARACION' in estados_disponibles:
            orden.estado = 'EN_REPARACION'
        elif 'REPARACION' in estados_disponibles:
            orden.estado = 'REPARACION'
        if hasattr(orden, 'diagnostico'):
            orden.diagnostico = f"{diag_actual} [PRESUPUESTO APROBADO]".strip()
        orden.save()
        return JsonResponse({
            'ok': True,
            'estado_presupuesto': 'APROBADO',
            'fase': 4,
            'mensaje': '¡Presupuesto aprobado! El equipo técnico comenzó la reparación.'
        })
    else:
        if hasattr(orden, 'diagnostico'):
            orden.diagnostico = f"{diag_actual} [REVISIÓN SOLICITADA]".strip()
        orden.save()
        return JsonResponse({
            'ok': True,
            'estado_presupuesto': 'RECHAZADO',
            'fase': 2,
            'mensaje': 'Solicitud registrada. El mecánico se contactará para ajustar el presupuesto.'
        })


@csrf_exempt
@require_POST
def api_suscribir_aviso(request):
    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'detail': 'Formato JSON inválido'}, status=400)

    orden_id = body.get('orden_id')
    if not orden_id:
        return JsonResponse({'detail': 'Orden no especificada'}, status=400)

    try:
        orden = OrdenReparacion.objects.get(id=orden_id)
    except OrdenReparacion.DoesNotExist:
        return JsonResponse({'detail': 'Orden no encontrada'}, status=404)

    diag_actual = getattr(orden, 'diagnostico', '') or ''
    if '[AVISO ACTIVO]' not in diag_actual and hasattr(orden, 'diagnostico'):
        orden.diagnostico = f"{diag_actual} [AVISO ACTIVO]".strip()
        orden.save()

    return JsonResponse({
        'ok': True,
        'aviso_activo': True,
        'mensaje': '¡Alerta activada! Te notificaremos apenas el vehículo esté listo para retirar.'
    })