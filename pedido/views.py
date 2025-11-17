from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Pedido, ItemPedido, Carrito, ItemCarrito
from client.models import Cliente
from product.models import Product, ProductSize


def _get_carrito_context(request):
    """Función auxiliar para obtener el carrito del usuario o sesión"""
    carrito = None
    if request.user.is_authenticated:
        try:
            cliente = Cliente.objects.get(user=request.user)
            carrito = Carrito.objects.filter(cliente=cliente).first()
        except Cliente.DoesNotExist:
            pass
    else:
        if request.session.session_key:
            carrito = Carrito.objects.filter(session_key=request.session.session_key).first()
    return {'carrito': carrito}


def _get_or_create_carrito(request):
    """Obtiene o crea un carrito para el usuario o sesión anónima"""
    if request.user.is_authenticated:
        try:
            cliente = Cliente.objects.get(user=request.user)
        except Cliente.DoesNotExist:
            cliente = Cliente.objects.create(user=request.user)
        carrito, created = Carrito.objects.get_or_create(cliente=cliente)
    else:
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
        carrito, created = Carrito.objects.get_or_create(session_key=session_key)
    
    return carrito


def agregar_al_carrito(request, producto_id):
    """Agregar producto al carrito"""
    if request.method == 'POST':
        producto = get_object_or_404(Product, id=producto_id)
        talla_id = request.POST.get('talla_id')
        cantidad = int(request.POST.get('cantidad', 1))
        
        # Validar talla
        talla = None
        if talla_id:
            talla = get_object_or_404(ProductSize, id=talla_id, producto=producto)
            if talla.stock < cantidad:
                messages.error(request, f'Solo quedan {talla.stock} unidades de la talla {talla.talla}.')
                return redirect('product:product_detail', slug=producto.slug)
        else:
            # Si el producto tiene tallas, es obligatorio seleccionar una
            if producto.tallas.exists():
                messages.error(request, 'Debes seleccionar una talla.')
                return redirect('product:product_detail', slug=producto.slug)
        
        # Validar stock general
        if producto.stock < cantidad:
            messages.error(request, f'Solo quedan {producto.stock} unidades disponibles.')
            return redirect('product:product_detail', slug=producto.slug)
        
        carrito = _get_or_create_carrito(request)
        
        # Verificar si ya existe el item
        item, created = ItemCarrito.objects.get_or_create(
            carrito=carrito,
            producto=producto,
            talla=talla,
            defaults={'cantidad': cantidad}
        )
        
        if not created:
            nueva_cantidad = item.cantidad + cantidad
            # Validar que no exceda el stock
            if talla and nueva_cantidad > talla.stock:
                messages.warning(request, f'No puedes añadir más de {talla.stock} unidades de esta talla.')
                return redirect('product:product_detail', slug=producto.slug)
            elif nueva_cantidad > producto.stock:
                messages.warning(request, f'No puedes añadir más de {producto.stock} unidades.')
                return redirect('product:product_detail', slug=producto.slug)
            
            item.cantidad = nueva_cantidad
            item.save()
            messages.success(request, f'Se actualizó la cantidad de {producto.nombre} en el carrito.')
        else:
            messages.success(request, f'✓ {producto.nombre} añadido al carrito.')
        
        # Redirigir según preferencia
        if 'redirect_to_cart' in request.POST:
            return redirect('carrito_compra')
        return redirect('product:product_detail', slug=producto.slug)
    
    return redirect('product:product_list')


def actualizar_cantidad_carrito(request, item_id):
    """Actualizar cantidad de un item del carrito"""
    if request.method == 'POST':
        carrito = _get_or_create_carrito(request)
        item = get_object_or_404(ItemCarrito, id=item_id, carrito=carrito)
        
        nueva_cantidad = int(request.POST.get('cantidad', 1))
        
        if nueva_cantidad > 0:
            # Verificar stock
            if item.talla and item.talla.stock < nueva_cantidad:
                messages.error(request, f'Stock insuficiente. Solo quedan {item.talla.stock} unidades.')
            elif item.producto.stock < nueva_cantidad:
                messages.error(request, f'Stock insuficiente. Solo quedan {item.producto.stock} unidades.')
            else:
                item.cantidad = nueva_cantidad
                item.save()
                messages.success(request, 'Cantidad actualizada.')
        else:
            item.delete()
            messages.success(request, 'Producto eliminado del carrito.')
    
    return redirect('carrito_compra')


def eliminar_del_carrito(request, item_id):
    """Eliminar item del carrito"""
    carrito = _get_or_create_carrito(request)
    item = get_object_or_404(ItemCarrito, id=item_id, carrito=carrito)
    nombre_producto = item.producto.nombre
    item.delete()
    messages.success(request, f'{nombre_producto} eliminado del carrito.')
    return redirect('carrito_compra')


def vaciar_carrito(request):
    """Vaciar todo el carrito"""
    if request.method == 'POST':
        carrito = _get_or_create_carrito(request)
        carrito.items.all().delete()
        messages.success(request, 'Carrito vaciado.')
    return redirect('carrito_compra')


def carrito_compra(request):
    """Vista del carrito de compra"""
    carrito = _get_or_create_carrito(request)
    items = ItemCarrito.objects.filter(carrito=carrito).select_related('producto', 'talla')
    
    subtotal = carrito.get_total()
    envio = 5.00 if subtotal > 0 and subtotal < 50 else 0
    total = subtotal + envio
    
    context = {
        'items': items,
        'subtotal': subtotal,
        'envio': envio,
        'total': total,
        'cantidad_items': carrito.get_cantidad_items(),
    }
    
    # Añadir carrito al contexto
    context.update(_get_carrito_context(request))
    
    return render(request, 'carrito_compra.html', context)


@login_required
def listado_pedidos(request):
    """Listado de pedidos del cliente"""
    try:
        cliente = Cliente.objects.get(user=request.user)
        pedidos = Pedido.objects.filter(cliente=cliente).order_by('-fecha_creacion')
    except Cliente.DoesNotExist:
        pedidos = []
        messages.warning(request, 'No tienes un perfil de cliente asociado.')

    context = {
        'pedidos': pedidos,
    }
    
    # Añadir carrito al contexto
    context.update(_get_carrito_context(request))
    
    return render(request, 'listado_pedidos.html', context)


@login_required
def detalle_pedido(request, pedido_id):
    """Detalle de un pedido específico"""
    cliente = Cliente.objects.get(user=request.user)
    pedido = get_object_or_404(Pedido, id=pedido_id, cliente=cliente)
    items = ItemPedido.objects.filter(pedido=pedido)

    context = {
        'pedido': pedido,
        'items': items,
        'total': pedido.total,
    }
    
    # Añadir carrito al contexto
    context.update(_get_carrito_context(request))
    
    return render(request, 'detalles_pedido.html', context)