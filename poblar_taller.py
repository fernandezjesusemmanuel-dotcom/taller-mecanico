import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from taller.models import Vehiculo, OrdenReparacion, Repuesto


def poblar():
    # 1. Crear Repuestos e Insumos (algunos en estado crítico para las alertas del Dashboard)
    repuestos_demo = [
        {'nombre': 'Kit Distribución Peugeot 1.6 16v', 'stock_actual': 4, 'stock_minimo': 2, 'precio': Decimal('85000.00')},
        {'nombre': 'Pastillas de Freno Delanteras Bosch', 'stock_actual': 1, 'stock_minimo': 4, 'precio': Decimal('32000.00')},  # Crítico
        {'nombre': 'Aceite Sintético 5W40 (Bidón 4L)', 'stock_actual': 2, 'stock_minimo': 5, 'precio': Decimal('48000.00')},    # Crítico
        {'nombre': 'Amortiguadores Delanteros Gas', 'stock_actual': 6, 'stock_minimo': 2, 'precio': Decimal('110000.00')},
        {'nombre': 'Batería 12x75 Reforzada', 'stock_actual': 1, 'stock_minimo': 3, 'precio': Decimal('145000.00')},          # Crítico
        {'nombre': 'Filtro de Aire y Habitáculo', 'stock_actual': 10, 'stock_minimo': 3, 'precio': Decimal('18500.00')},
    ]

    campos_repuesto = {f.name for f in Repuesto._meta.get_fields()}
    for r_data in repuestos_demo:
        defaults = {}
        if 'stock_actual' in campos_repuesto:
            defaults['stock_actual'] = r_data['stock_actual']
        if 'stock_minimo' in campos_repuesto:
            defaults['stock_minimo'] = r_data['stock_minimo']
        if 'stock_minimo_alerta' in campos_repuesto:
            defaults['stock_minimo_alerta'] = r_data['stock_minimo']
        if 'precio' in campos_repuesto:
            defaults['precio'] = r_data['precio']
        if 'precio_unitario' in campos_repuesto:
            defaults['precio_unitario'] = r_data['precio']
        if 'activo' in campos_repuesto:
            defaults['activo'] = True

        Repuesto.objects.update_or_create(nombre=r_data['nombre'], defaults=defaults)

    # 2. Normalizar patentes previas con espacios (ej. 'kbh 106' -> 'KBH106')
    for v in Vehiculo.objects.all():
        pat_limpia = v.patente.replace(' ', '').replace('-', '').strip().upper()
        if v.patente != pat_limpia and not Vehiculo.objects.filter(patente=pat_limpia).exists():
            v.patente = pat_limpia
            v.save()

    # 3. Crear Flota de Vehículos (con campo 'anio' incluido)
    flota_demo = [
        {
            'patente': 'KBH106',
            'marca': 'Peugeot',
            'modelo': '207 XS Compact',
            'anio': 2011,
            'dueño_nombre': 'Jesús Fernández',
            'dueño_telefono': '2615962434',
            'estado': 'EN_REPARACION',
            'total_estimado': Decimal('165000.00'),
            'horas_estimadas': Decimal('3.5'),
            'diagnostico': 'Cambio de kit de distribución completo, revisión de pastillas de freno delanteras y escaneo electrónico OBC. [PRESUPUESTO APROBADO]',
        },
        {
            'patente': 'AF450XZ',
            'marca': 'Toyota',
            'modelo': 'Hilux SRX Pickup',
            'anio': 2022,
            'dueño_nombre': 'Martín Gómez',
            'dueño_telefono': '2615962434',
            'estado': 'DIAGNOSTICO',
            'total_estimado': Decimal('290000.00'),
            'horas_estimadas': Decimal('5.0'),
            'diagnostico': 'Revisión de suspensión delantera, amortiguadores, alineación 3D y control de transmisión.',
        },
        {
            'patente': 'AD892KL',
            'marca': 'Renault',
            'modelo': 'Duster 4WD SUV',
            'anio': 2019,
            'dueño_nombre': 'Lucía Quiroga',
            'dueño_telefono': '2615962434',
            'estado': 'REPUESTOS',
            'total_estimado': Decimal('195000.00'),
            'horas_estimadas': Decimal('4.0'),
            'diagnostico': 'Reemplazo de batería 12V, prueba de alternador y control de sonda lambda en escape. [AVISO ACTIVO]',
        },
        {
            'patente': 'AE123BC',
            'marca': 'Volkswagen',
            'modelo': 'Vento 2.0 TSI',
            'anio': 2020,
            'dueño_nombre': 'Carlos Salman',
            'dueño_telefono': '2615962434',
            'estado': 'LISTO',
            'total_estimado': Decimal('120000.00'),
            'horas_estimadas': Decimal('0.5'),
            'diagnostico': 'Service completo de fluidos, filtros y verificación de frenos ABS finalizada. [PRESUPUESTO APROBADO]',
        },
    ]

    campos_vehiculo = {f.name for f in Vehiculo._meta.get_fields()}
    campos_orden = {f.name for f in OrdenReparacion._meta.get_fields()}
    estados_validos = [c[0] for c in OrdenReparacion._meta.get_field('estado').choices]

    for item in flota_demo:
        v_defaults = {
            'marca': item['marca'],
            'modelo': item['modelo'],
        }
        if 'anio' in campos_vehiculo:
            v_defaults['anio'] = item['anio']
        if 'año' in campos_vehiculo:
            v_defaults['año'] = item['anio']
        if 'dueño_nombre' in campos_vehiculo:
            v_defaults['dueño_nombre'] = item['dueño_nombre']
        if 'dueno_nombre' in campos_vehiculo:
            v_defaults['dueno_nombre'] = item['dueño_nombre']
        if 'dueño_telefono' in campos_vehiculo:
            v_defaults['dueño_telefono'] = item['dueño_telefono']
        if 'dueno_telefono' in campos_vehiculo:
            v_defaults['dueno_telefono'] = item['dueño_telefono']

        vehiculo, _ = Vehiculo.objects.update_or_create(
            patente=item['patente'],
            defaults=v_defaults
        )

        estado_elegido = item['estado']
        if estado_elegido == 'EN_REPARACION' and 'EN_REPARACION' not in estados_validos and 'REPARACION' in estados_validos:
            estado_elegido = 'REPARACION'

        orden_defaults = {
            'estado': estado_elegido,
            'total_estimado': item['total_estimado'],
        }
        if 'diagnostico' in campos_orden:
            orden_defaults['diagnostico'] = item['diagnostico']
        if 'descripcion_falla' in campos_orden:
            orden_defaults['descripcion_falla'] = item['diagnostico']
        if 'horas_estimadas' in campos_orden:
            orden_defaults['horas_estimadas'] = item['horas_estimadas']

        orden_existente = OrdenReparacion.objects.filter(vehiculo=vehiculo).first()
        if orden_existente:
            for k, v in orden_defaults.items():
                setattr(orden_existente, k, v)
            orden_existente.save()
        else:
            OrdenReparacion.objects.create(vehiculo=vehiculo, **orden_defaults)

    print(">>> Flota de 4 vehículos (Hatchback, Pickup, SUV y Sedán), repuestos y órdenes cargados con éxito.")


if __name__ == '__main__':
    poblar()