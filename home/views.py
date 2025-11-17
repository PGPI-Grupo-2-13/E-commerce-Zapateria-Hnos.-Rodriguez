from django.shortcuts import render
from product.models import Product
from pedido.models import Carrito, ItemCarrito

def home(request):
    productos = Product.objects.all()
    carrito = None
    carrito_items = []
    if request.user.is_authenticated:
        cliente = getattr(request.user, 'cliente', None)
        if cliente:
            carrito, _ = Carrito.objects.get_or_create(cliente=cliente)
            carrito_items = ItemCarrito.objects.filter(carrito=carrito)
            for item in carrito_items:
                item.subtotal = item.cantidad * item.producto.precio
            total = sum(item.subtotal for item in carrito_items)
        else:
            total = 0
    else:
        total = 0

    return render(request, 'home.html', {
        'productos': productos,
        'carrito': carrito,
        'carrito_items': carrito_items,
        'carrito_total': total
    })
