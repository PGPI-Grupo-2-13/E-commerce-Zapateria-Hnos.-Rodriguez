from django.contrib import admin
from .models import Pedido, ItemPedido, Carrito, ItemCarrito

admin.site.register(Pedido)
admin.site.register(ItemPedido)
admin.site.register(Carrito)
admin.site.register(ItemCarrito)
