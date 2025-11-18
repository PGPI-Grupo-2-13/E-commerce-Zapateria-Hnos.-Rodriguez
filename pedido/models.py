from django.db import models

from client.models import Cliente
from product.models import Product

# Create your models here.
class Pedido(models.Model):

    class EstadoPedido(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        PAGADO = 'PAGADO', 'Pagado'
        ENVIADO = 'ENVIADO', 'Enviado'
        COMPLETADO = 'COMPLETADO', 'Completado'
        CANCELADO = 'CANCELADO', 'Cancelado'

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    numero_pedido = models.CharField(max_length=120, unique=True, help_text="Número de pedido único")
    estado = models.CharField(
        max_length=20,
        choices=EstadoPedido.choices,
        default=EstadoPedido.PENDIENTE
    )


    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    impuestos = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    coste_entrega = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    descuento = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)


    metodo_pago = models.CharField(max_length=100, blank=True, null=True)
    direccion_envio = models.TextField(blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)


    def __str__(self):
        return f'Pedido {self.numero_pedido} de {self.cliente.user.username}'

class ItemPedido(models.Model):
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="items"
    )
 
    producto = models.ForeignKey(
        Product,
        on_delete=models.CASCADE, 
    )
    
    talla = models.CharField(max_length=50, blank=True, null=True)
    cantidad = models.PositiveIntegerField(default=1)

    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"

class Carrito(models.Model):
    # El cliente ahora debe ser opcional (null=True, blank=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, null=True, blank=True)
    
    # AGREGA ESTE CAMPO NUEVO:
    session_key = models.CharField(max_length=40, null=True, blank=True)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.cliente:
            return f"Carrito de {self.cliente}"
        return f"Carrito Anónimo ({self.session_key})"

    def get_total(self):
        total = 0
        for item in self.itemcarrito_set.all():
            # CORRECCIÓN: Añadimos () después de precio_final
            total += item.producto.precio_final * item.cantidad 
        return total

    def get_cantidad_items(self):
        return sum(item.cantidad for item in self.itemcarrito_set.all())

class ItemCarrito(models.Model):
    carrito = models.ForeignKey(
        Carrito,
        on_delete=models.CASCADE
    )
    
    producto = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )
    
    talla = models.CharField(max_length=50, blank=True, null=True)
    cantidad = models.PositiveIntegerField(default=1)


    def __str__(self):
        return (f"{self.cantidad} x {self.producto.nombre}")