from django.contrib import admin
from .models import Vehiculo, Repuesto, OrdenReparacion, DetalleOrden

@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = ('patente', 'marca', 'modelo', 'dueño_nombre', 'creado')
    search_fields = ('patente', 'dueño_nombre')

@admin.register(Repuesto)
class RepuestoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'precio', 'stock_actual', 'activo')
    list_editable = ('precio', 'stock_actual', 'activo')
    search_fields = ('nombre', 'codigo')
    list_filter = ('activo',)

class DetalleOrdenInline(admin.TabularInline):
    model = DetalleOrden
    extra = 0

@admin.register(OrdenReparacion)
class OrdenReparacionAdmin(admin.ModelAdmin):
    list_display = ('id', 'vehiculo', 'estado', 'fecha_ingreso', 'total_estimado')
    list_filter = ('estado', 'fecha_ingreso')
    list_editable = ('estado',)
    search_fields = ('vehiculo__patente',)
    date_hierarchy = 'fecha_ingreso'
    inlines = [DetalleOrdenInline]