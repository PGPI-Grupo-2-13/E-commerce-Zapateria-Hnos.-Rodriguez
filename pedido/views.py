from django.shortcuts import render
from django.template import loader
from django.shortcuts import render
from .models import Pedido, ItemPedido, Carrito, ItemCarrito

def index_pedido(request):
    pedidos = Pedido.objects.all()
    pedido = pedidos.first()
    items = ItemPedido.objects.filter(pedido=pedido)
    contexto = {
        'pedido': pedido,
        'items': items,
    }
    plantilla = loader.get_template('pedido.html')
    return render(request, 'pedido.html', contexto)

def carrito_compra(request):
    carrito = Carrito.objects.first()
    
    if not carrito:
        carrito = Carrito.objects.create()
    
    items = ItemCarrito.objects.filter(carrito=carrito)
    
    subtotal = sum(item.cantidad * item.producto.precio for item in items) if items.exists() else 0
    
    contexto = {
        'carrito': carrito,
        'items': items,
        'subtotal': subtotal,
        'envio': 0,
        'total': subtotal,
    }
    
    return render(request, 'carrito_compra.html', contexto)