from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
# Importaciones necesarias
from .models import Pedido, ItemPedido, Carrito, ItemCarrito
from client.models import Cliente
from product.models import Product, ProductSize


# --- Funciones Auxiliares ---
def _get_carrito_context(request):
    """Función auxiliar para obtener el carrito del usuario o sesión"""
    carrito = None
    if request.user.is_authenticated:
        try:
            cliente = Cliente.objects.get(user=request.user)
            # Aseguramos que solo buscamos un carrito si el cliente existe
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
            # Busca o crea el cliente si no existe (esto lo hace tu signal post_save, pero es bueno tener un fallback)
            cliente = Cliente.objects.get(user=request.user) 
        except Cliente.DoesNotExist:
            cliente = Cliente.objects.create(user=request.user, direccion='', ciudad='', codigo_postal='') # Crea cliente con valores por defecto
            
        # Corregido a filter().first() si Carrito ya no es OneToOneField
        carrito, created = Carrito.objects.get_or_create(cliente=cliente, defaults={'session_key': None}) 
        
        # Si tienes carritos anónimos sin migrar, este código los asocia:
        if not created and carrito.session_key:
             carrito.session_key = None
             carrito.save()
    else:
        if not request.session.session_key:
            request.session.create()
        
        session_key = request.session.session_key
        
        carrito, created = Carrito.objects.get_or_create(
            session_key=session_key,
            defaults={'cliente': None}
        )
    
    return carrito


def _get_stock_object(request, item):
    """Determina si el ítem usa ProductSize o Product stock, y lo devuelve."""
    producto = item.producto
    if item.talla:
        try:
            # Buscamos el objeto ProductSize usando la cadena de la talla
            return ProductSize.objects.get(
                producto=producto, 
                talla=item.talla
            )
        except ProductSize.DoesNotExist:
            # Fallback: Si la talla no existe, usamos el stock del producto general
            # Ahora 'request' sí está definido porque lo pasamos como argumento
            messages.warning(request, f"Advertencia: Talla '{item.talla}' no encontrada. Usando stock de producto general.")
            return producto
    return producto


# --- Vistas de Carrito ---

def agregar_al_carrito(request, producto_id):
    """Agregar producto al carrito y reducir el stock."""
    if request.method == 'POST':
        producto = get_object_or_404(Product, id=producto_id)
        talla_id = request.POST.get('talla_id')
        cantidad = int(request.POST.get('cantidad', 1))
        
        talla_obj = None # Objeto ProductSize
        talla_str = None # Cadena de la talla (ej: '43')
        
        stock_object = producto
        max_stock = producto.stock
        
        # 1. Validar y determinar objeto de stock
        if talla_id:
            talla_obj = get_object_or_404(ProductSize, id=talla_id, producto=producto)
            talla_str = talla_obj.talla  # <-- CORRECCIÓN: Guardamos solo la talla como string
            stock_object = talla_obj
            max_stock = talla_obj.stock
            
            if max_stock < cantidad:
                messages.error(request, f'Solo quedan {max_stock} unidades de la talla {talla_obj.talla}.')
                return redirect('product:product_detail', slug=producto.slug)
        else:
            # Si el producto tiene tallas, es obligatorio seleccionar una (mantenemos la validación original)
            if producto.tallas.exists():
                messages.error(request, 'Debes seleccionar una talla.')
                return redirect('product:product_detail', slug=producto.slug)
            
            # Validar stock general si no se usan tallas
            if max_stock < cantidad:
                messages.error(request, f'Solo quedan {max_stock} unidades disponibles.')
                return redirect('product:product_detail', slug=producto.slug)
        
        carrito = _get_or_create_carrito(request)
        
        # Verificar si ya existe el item
        item, created = ItemCarrito.objects.get_or_create(
            carrito=carrito,
            producto=producto,
            talla=talla_str, # <-- Usamos solo la cadena de la talla
            defaults={'cantidad': cantidad}
        )
        
        unidades_a_restar = 0
        stock_valido = True
        
        if not created:
            nueva_cantidad = item.cantidad + cantidad
            
            # Stock real disponible (stock actual en BD + lo que ya está reservado por este ítem)
            stock_real_disponible = max_stock + item.cantidad 
            
            # Validar que no exceda el stock total (reservado + disponible)
            if nueva_cantidad > stock_real_disponible:
                messages.warning(request, f'No puedes añadir más de {max_stock} unidades de este ítem. Ya tienes {item.cantidad} en el carrito.')
                stock_valido = False
            else:
                unidades_a_restar = cantidad
                item.cantidad = nueva_cantidad
                item.save()
        else:
            unidades_a_restar = cantidad

        # 2. DEDUCCIÓN DE STOCK CRÍTICA
        if stock_valido and unidades_a_restar > 0:
            stock_object.stock -= unidades_a_restar
            stock_object.save()
        
        # Redirigir según preferencia (con lógica para abrir sidebar)
        if 'redirect_to_cart' in request.POST:
            return redirect('carrito_compra')
        
        # Si la redirección original incluía abrir el sidebar:
        referer = request.META.get('HTTP_REFERER')
        if referer:
            url = referer
            # Evitamos duplicar '?cart_open=true' si ya está presente
            if 'cart_open=true' not in url:
                if '?' in url:
                    url += '&cart_open=true'
                else:
                    url += '?cart_open=true'
            return redirect(url)
            
        return redirect('product:product_detail', slug=producto.slug)
    
    return redirect('product:product_list')


def actualizar_cantidad_carrito(request, item_id):
    """Actualizar cantidad de un item del carrito y ajustar el stock."""
    if request.method == 'POST':
        carrito = _get_or_create_carrito(request)
        
        # Obtenemos el ítem (incluye producto relacionado para _get_stock_object)
        item = get_object_or_404(
            ItemCarrito.objects.select_related('producto'),  
            id=item_id, 
            carrito=carrito
        ) 
        
        cantidad_original = item.cantidad 
        
        try:
            nueva_cantidad = int(request.POST.get('cantidad', 1))
        except ValueError:
            messages.error(request, 'La cantidad debe ser un número válido.')
            return redirect('carrito_compra')
            
        if nueva_cantidad < 0:
            # Forzamos la eliminación si la cantidad es inválida
            nueva_cantidad = 0 
        
        # 1. Obtener el objeto de stock real
        objeto_stock = _get_stock_object(request,item)
        
        # Calculamos el stock real que había antes: stock disponible + cantidad reservada actualmente
        stock_disponible_real = objeto_stock.stock + cantidad_original 
        
        
        if nueva_cantidad == 0:
            # CASO 1: ELIMINACIÓN
            
            # Devolvemos el stock reservado al producto/talla
            objeto_stock.stock += cantidad_original
            objeto_stock.save()  
            
            item.delete()
        
        elif nueva_cantidad > stock_disponible_real:
            # CASO 2: STOCK INSUFICIENTE (Máximo que se puede alcanzar)
            
            messages.error(request, f'Stock insuficiente. Máximo disponible: {stock_disponible_real} unidades.')
            # No actualizamos el ítem, dejamos la cantidad_original.
            
        else:
            # CASO 3: ACTUALIZACIÓN VÁLIDA
            
            # Calculamos la diferencia
            diferencia = nueva_cantidad - cantidad_original
            
            # Aplicamos la diferencia al stock (si diferencia es +, stock baja; si es -, stock sube)
            objeto_stock.stock -= diferencia
            objeto_stock.save()  
            
            # Guardamos la nueva cantidad en el ítem del carrito
            item.cantidad = nueva_cantidad
            item.save()
            
    # Redirección: mantenemos la lógica original o redirigimos al carrito
    referer = request.META.get('HTTP_REFERER')
    
    if referer and 'cart_open' in referer:
        return redirect(referer) # Si ya tenía cart_open, redirigimos a la misma URL
            
    return redirect('carrito_compra')


def eliminar_del_carrito(request, item_id):
    """Eliminar item del carrito y devolver el stock a la tienda."""
    carrito = _get_or_create_carrito(request)
    
    item = get_object_or_404(
        ItemCarrito.objects.select_related('producto'), 
        id=item_id, 
        carrito=carrito
    ) 
    
    nombre_producto = item.producto.nombre
    cantidad_a_devolver = item.cantidad

    # Determinar el objeto de stock a modificar
    objeto_stock = _get_stock_object(request,item)
            
    # Devolver el stock
    objeto_stock.stock += cantidad_a_devolver
    objeto_stock.save()

    item.delete()
    
    # Redirección sidebar
    referer = request.META.get('HTTP_REFERER')
    
    if referer and 'cart_open' in referer:
        return redirect(referer)
            
    return redirect('carrito_compra')


def vaciar_carrito(request):
    """Vaciar todo el carrito"""
    if request.method == 'POST':
        carrito = _get_or_create_carrito(request)
        
        # Devolver stock de todos los items antes de eliminarlos
        for item in carrito.itemcarrito_set.all():
            objeto_stock = _get_stock_object(request,item)
            objeto_stock.stock += item.cantidad
            objeto_stock.save()

        carrito.itemcarrito_set.all().delete()
        
    return redirect('carrito_compra')


def carrito_compra(request):
    """Vista del carrito de compra"""
    carrito = _get_or_create_carrito(request)
    # Seleccionamos 'producto' para evitar consultas N+1
    items = ItemCarrito.objects.filter(carrito=carrito).select_related('producto') 
    
    # ... (el resto de la vista sigue igual) ...
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
    
    context.update(_get_carrito_context(request))
    
    return render(request, 'detalles_pedido.html', context)