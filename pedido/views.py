from django.shortcuts import render, get_object_or_404
from .models import Pedido, ItemPedido, Carrito, ItemCarrito

def listado_pedidos(request):
    pedidos = Pedido.objects.filter(cliente=request.user).order_by('-fecha_creacion')
    
    contexto = {
        'pedidos': pedidos
    }
    return render(request, 'listado_pedidos.html', contexto)

def detalle_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id, cliente=request.user)

    items = ItemPedido.objects.filter(pedido=pedido)

    for item in items:
        item.subtotal_item = item.cantidad * item.precio_unitario

    # 🔥 Calcular total del pedido
    total = pedido.subtotal + pedido.coste_entrega + pedido.impuestos - pedido.descuento

    contexto = {
        'pedido': pedido,
        'items': items,
        'total': total,
    }

    return render(request, 'detalles_pedido.html', contexto)

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
