from django.core.validators import MinValueValidator
from django.db import models

class Vehiculo(models.Model):
    patente = models.CharField(max_length=15, unique=True)
    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=50)
    anio = models.PositiveIntegerField(verbose_name="Año")
    dueño_nombre = models.CharField(max_length=150)
    dueño_telefono = models.CharField(max_length=30)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Vehículo"
        verbose_name_plural = "Vehículos"

    def __str__(self):
        return f"{self.patente} - {self.marca} {self.modelo}"

class Repuesto(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    codigo = models.CharField(max_length=50, blank=True, null=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    stock_actual = models.PositiveIntegerField(default=0)
    stock_minimo_alerta = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Repuesto / Insumo"
        verbose_name_plural = "Repuestos e Insumos"

    def esta_bajo_stock(self):
        return self.stock_actual <= self.stock_minimo_alerta

    def __str__(self):
        return f"{self.nombre} (Stock: {self.stock_actual})"

class OrdenReparacion(models.Model):
    ESTADOS = [
        ('RECIBIDO', 'Recibido / En espera'),
        ('DIAGNOSTICO', 'En diagnóstico'),
        ('REPUESTOS', 'Esperando repuestos'),
        ('REPARACION', 'En reparación'),
        ('LISTO', 'Listo para retirar'),
        ('ENTREGADO', 'Vehículo entregado'),
    ]

    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, related_name='ordenes')
    fecha_ingreso = models.DateTimeField(auto_now_add=True)
    fecha_estimada_entrega = models.DateTimeField(blank=True, null=True)
    diagnostico_preliminar = models.TextField(help_text="Falla reportada por el cliente")
    estado = models.CharField(max_length=20, choices=ESTADOS, default='RECIBIDO')
    mano_de_obra = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    total_estimado = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)

    class Meta:
        verbose_name = "Orden de Reparación"
        verbose_name_plural = "Órdenes de Reparación"
        ordering = ['-fecha_ingreso']

    def __str__(self):
        return f"Orden #{self.id} - {self.vehiculo.patente}"

class DetalleOrden(models.Model):
    orden = models.ForeignKey(OrdenReparacion, on_delete=models.CASCADE, related_name='repuestos_usados')
    repuesto = models.ForeignKey(Repuesto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Repuesto Usado"
        verbose_name_plural = "Repuestos Usados"

    def __str__(self):
        return f"{self.cantidad}x {self.repuesto.nombre}"