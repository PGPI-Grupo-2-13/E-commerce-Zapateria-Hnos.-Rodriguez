from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse 
from django.conf import settings
from decimal import Decimal
from django.utils import timezone

# --- Importaciones de tus modelos ---
from .models import Pedido, ItemPedido, Carrito, ItemCarrito
from client.models import Cliente
from product.models import Product, ProductSize
from .stripe_api import create_payment_intent


# --- Funciones Auxiliares ---

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
    """Obtiene o crea un carrito de forma robusta (elimina duplicados si existen)"""
    carrito = None
    
    if request.user.is_authenticated:
        # LOGICA PARA USUARIO REGISTRADO
        try:
            cliente = Cliente.objects.get(user=request.user) 
        except Cliente.DoesNotExist:
            cliente = Cliente.objects.create(user=request.user, direccion='', ciudad='', codigo_postal='') 
        
        # Buscamos carritos existentes para este cliente
        qs = Carrito.objects.filter(cliente=cliente)
        
        if qs.exists():
            # Si existe uno o más, cogemos el primero (el más antiguo)
            carrito = qs.first()
            # ¡AUTOCORRECCIÓN! Si hay duplicados, los borramos para evitar el error 500
            if qs.count() > 1:
                for duplicado in qs[1:]:
                    duplicado.delete()
        else:
            # Si no existe, lo creamos
            carrito = Carrito.objects.create(cliente=cliente, session_key=None)
        
        # Asegurar que no tenga session_key si es usuario logueado
        if carrito.session_key:
            carrito.session_key = None
            carrito.save()

    else:
        # LOGICA PARA USUARIO ANÓNIMO
        if not request.session.session_key:
            request.session.create()
        
        session_key = request.session.session_key
        
        qs = Carrito.objects.filter(session_key=session_key)
        
        if qs.exists():
            carrito = qs.first()
            if qs.count() > 1:
                for duplicado in qs[1:]:
                    duplicado.delete()
        else:
            carrito = Carrito.objects.create(session_key=session_key, cliente=None)
    
    return carrito


def _get_stock_object(request, item):
    """Determina si el ítem usa ProductSize o Product stock, y lo devuelve."""
    producto = item.producto
    if item.talla:
        try:
            return ProductSize.objects.get(
                producto=producto, 
                talla=item.talla
            )
        except ProductSize.DoesNotExist:
            messages.warning(request, f"Advertencia: Talla '{item.talla}' no encontrada. Usando stock de producto general.")
            return producto
    return producto


def _is_ajax(request):
    """Detecta si la petición viene de JavaScript (Sidebar)"""
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'


# --- Vistas de Carrito ---

def agregar_al_carrito(request, producto_id):
    """Agregar producto al carrito y reducir el stock."""
    if request.method == 'POST':
        producto = get_object_or_404(Product, id=producto_id)
        talla_id = request.POST.get('talla_id')
        
        try:
            cantidad = int(request.POST.get('cantidad', 1))
        except ValueError:
            cantidad = 1

        if cantidad <= 0:
            messages.error(request, 'La cantidad debe ser positiva.')
            return redirect('product:product_detail', slug=producto.slug)
        
        talla_obj = None 
        talla_str = None 
        
        stock_object = producto
        max_stock = producto.stock
        
        # 1. Validar stock
        if talla_id:
            try:
                talla_obj = ProductSize.objects.get(id=talla_id, producto=producto)
                talla_str = talla_obj.talla 
                stock_object = talla_obj
                max_stock = talla_obj.stock
            except ProductSize.DoesNotExist:
                 messages.error(request, 'La talla seleccionada no es válida.')
                 return redirect('product:product_detail', slug=producto.slug)

            if max_stock < cantidad:
                messages.error(request, f'Solo quedan {max_stock} unidades de la talla {talla_obj.talla}.')
                return redirect('product:product_detail', slug=producto.slug)
        else:
            if producto.tallas.exists():
                messages.error(request, 'Debes seleccionar una talla.')
                return redirect('product:product_detail', slug=producto.slug)
            
            if max_stock < cantidad:
                messages.error(request, f'Solo quedan {max_stock} unidades disponibles.')
                return redirect('product:product_detail', slug=producto.slug)
        
        carrito = _get_or_create_carrito(request)
        
        # Agregar item
        item, created = ItemCarrito.objects.get_or_create(
            carrito=carrito,
            producto=producto,
            talla=talla_str, 
            defaults={'cantidad': cantidad}
        )
        
        unidades_a_restar = 0
        stock_valido = True
        
        if not created:
            nueva_cantidad = item.cantidad + cantidad
            stock_real_disponible = max_stock + item.cantidad 
            
            if nueva_cantidad > stock_real_disponible:
                messages.warning(request, f'No puedes añadir más de {stock_real_disponible} unidades. Ya tienes {item.cantidad}.')
                stock_valido = False
            else:
                unidades_a_restar = cantidad
                item.cantidad = nueva_cantidad
                item.save()
        else:
            unidades_a_restar = cantidad

        # 2. Restar Stock
        if stock_valido and unidades_a_restar > 0:
            stock_object.stock -= unidades_a_restar
            stock_object.save()
        
        # Respuesta AJAX (para el futuro si lo implementas en agregar)
        if _is_ajax(request):
            return JsonResponse({'success': True, 'message': 'Producto añadido.'})
            
        if 'redirect_to_cart' in request.POST:
            return redirect('carrito_compra')
        
        referer = request.META.get('HTTP_REFERER')
        if referer:
            url = referer
            if 'cart_open=true' not in url:
                url += '&cart_open=true' if '?' in url else '?cart_open=true'
            return redirect(url)
            
        return redirect('product:product_detail', slug=producto.slug)
    
    return redirect('product:product_list')


def actualizar_cantidad_carrito(request, item_id):
    """Actualizar cantidad de un item del carrito y ajustar el stock."""
    carrito = _get_or_create_carrito(request)
    
    try:
        item = ItemCarrito.objects.select_related('producto').get(id=item_id, carrito=carrito) 
    except ItemCarrito.DoesNotExist:
        if _is_ajax(request):
            return JsonResponse({'success': False, 'message': 'Ítem no encontrado.'}, status=404)
        return redirect('carrito_compra')
    
    cantidad_original = item.cantidad 
    
    try:
        nueva_cantidad = int(request.POST.get('cantidad', 1))
    except ValueError:
        if _is_ajax(request):
            return JsonResponse({'success': False, 'message': 'Cantidad inválida.'}, status=400)
        return redirect('carrito_compra')
        
    if nueva_cantidad < 0: nueva_cantidad = 0 
    
    objeto_stock = _get_stock_object(request, item)
    stock_disponible_real = objeto_stock.stock + cantidad_original 
    
    if nueva_cantidad == 0:
        # ELIMINAR
        try:
            objeto_stock.stock += cantidad_original
            objeto_stock.save() 
            item.delete()
        except Exception as e:
            if _is_ajax(request): return JsonResponse({'success': False, 'message': 'Error al eliminar.'}, status=500)
            messages.error(request, 'Error al eliminar.')
            return redirect('carrito_compra')
            
        if _is_ajax(request): return JsonResponse({'success': True, 'message': 'Ítem eliminado.'})
        messages.success(request, 'Item eliminado.')
    
    elif nueva_cantidad > stock_disponible_real:
        # STOCK INSUFICIENTE
        msg = f'Stock insuficiente. Máximo: {stock_disponible_real}'
        if _is_ajax(request): return JsonResponse({'success': False, 'message': msg, 'max_qty': stock_disponible_real}, status=400)
        messages.error(request, msg)
        
    else:
        # ACTUALIZAR
        diferencia = nueva_cantidad - cantidad_original
        try:
            objeto_stock.stock -= diferencia
            objeto_stock.save() 
            item.cantidad = nueva_cantidad
            item.save()
            if _is_ajax(request): return JsonResponse({'success': True, 'message': 'Cantidad actualizada.'})
            messages.success(request, f'Cantidad actualizada a {nueva_cantidad}.')
        except Exception:
            if _is_ajax(request): return JsonResponse({'success': False, 'message': 'Error de servidor.'}, status=500)
            messages.error(request, 'Error al actualizar stock.')

    referer = request.META.get('HTTP_REFERER')
    if referer and ('cart_open' in referer or 'carrito_compra' in referer):
        return redirect(referer) 
            
    return redirect('carrito_compra')


def eliminar_del_carrito(request, item_id):
    """Eliminar item del carrito (CORREGIDO para evitar error 500)"""
    
    if request.method == 'POST':
        carrito = _get_or_create_carrito(request)
        
        # 1. Obtener ítem de forma segura
        try:
            item = ItemCarrito.objects.select_related('producto').get(id=item_id, carrito=carrito) 
        except ItemCarrito.DoesNotExist:
            # Si ya no existe, devolvemos éxito al AJAX para que se actualice la UI, o redirigimos
            if _is_ajax(request):
                return JsonResponse({'success': True, 'message': 'El producto ya no estaba en el carrito.'})
            messages.warning(request, 'El producto ya no se encuentra en el carrito.')
            return redirect('carrito_compra')
            
        nombre_producto = item.producto.nombre
        cantidad_a_devolver = item.cantidad

        # 2. Lógica crítica con manejo de errores
        try:
            objeto_stock = _get_stock_object(request, item)
            objeto_stock.stock += cantidad_a_devolver
            objeto_stock.save()
            item.delete()
            
        except Exception as e:
            print(f"Error CRÍTICO eliminando item {item_id}: {e}")
            if _is_ajax(request):
                return JsonResponse({'success': False, 'message': 'Error del servidor al procesar la eliminación.'}, status=500)
            messages.error(request, 'Error del servidor al eliminar el producto.')
            return redirect('carrito_compra')

        # 3. Respuesta Exitosa
        if _is_ajax(request):
            return JsonResponse({'success': True, 'message': f'{nombre_producto} eliminado.'})
            
        messages.success(request, f'"{nombre_producto}" eliminado del carrito.')
        return redirect('carrito_compra')
    
    # Si no es POST
    if _is_ajax(request): return JsonResponse({'success': False}, status=405)
    return redirect('carrito_compra')


def vaciar_carrito(request):
    """Vaciar todo el carrito"""
    if request.method == 'POST':
        carrito = _get_or_create_carrito(request)
        try:
            for item in carrito.itemcarrito_set.all():
                objeto_stock = _get_stock_object(request,item)
                objeto_stock.stock += item.cantidad
                objeto_stock.save()
            carrito.itemcarrito_set.all().delete()
            
            if _is_ajax(request): return JsonResponse({'success': True, 'message': 'Carrito vaciado.'})
            messages.success(request, 'Tu carrito ha sido vaciado.')
        
        except Exception as e:
            if _is_ajax(request): return JsonResponse({'success': False, 'message': 'Error al vaciar.'}, status=500)
            messages.error(request, 'Error al vaciar el carrito.')
            
    return redirect('carrito_compra')


def carrito_compra(request):
    """Vista del carrito de compra"""
    carrito = _get_or_create_carrito(request)
    items = ItemCarrito.objects.filter(carrito=carrito).select_related('producto') 
    
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

def checkout_pedido(request, numero_pedido):
    """
    Vista para iniciar el pago de un pedido concreto.
    """
    pedido = get_object_or_404(Pedido, numero_pedido=numero_pedido)

    # Si ya está pagado, lo mandamos directamente a la página de éxito
    if pedido.estado_pago == "pagado":
        return redirect("pedido_pago_exito", numero_pedido=numero_pedido)

    # Si aún no hemos creado el PaymentIntent en Stripe, lo creamos ahora
    if not pedido.stripe_payment_intent_id:
        payment_intent = create_payment_intent(pedido)

        if payment_intent is None:
            # Algo fue mal con Stripe
            contexto_error = {
                "pedido": pedido,
                "error": "No se pudo iniciar el pago con Stripe. Inténtalo más tarde."
            }
            return render(request, "pago_error.html", contexto_error)

        pedido.stripe_payment_intent_id = payment_intent.id
        pedido.stripe_client_secret = payment_intent.client_secret
        pedido.save()

    context = {
        "pedido": pedido,
        "stripe_public_key": settings.STRIPE_PUBLIC_KEY,
        "client_secret": pedido.stripe_client_secret,
    }
    return render(request, "pasarela_pago.html", context)


def pedido_pago_exito(request, numero_pedido):
    """
    Vista que se muestra cuando Stripe confirma el pago correctamente.
    """
    pedido = get_object_or_404(Pedido, numero_pedido=numero_pedido)

    # Actualizamos estados
    pedido.estado_pago = "pagado"
    pedido.estado = Pedido.EstadoPedido.PAGADO
    pedido.save()

    return render(request, "pago_exito.html", {"pedido": pedido})


def pedido_pago_error(request, numero_pedido):
    """
    Vista a la que redirigimos si algo falla en el pago.
    """
    pedido = get_object_or_404(Pedido, numero_pedido=numero_pedido)

    pedido.estado_pago = "fallido"
    pedido.save()

    return render(request, "pago_error.html", {"pedido": pedido})


@login_required
def listado_pedidos(request):
    try:
        cliente = Cliente.objects.get(user=request.user)
        pedidos = Pedido.objects.filter(cliente=cliente).order_by('-fecha_creacion')
    except Cliente.DoesNotExist:
        pedidos = []
        messages.warning(request, 'No tienes un perfil de cliente asociado.')
    context = {'pedidos': pedidos}
    context.update(_get_carrito_context(request))
    return render(request, 'listado_pedidos.html', context)


@login_required
def detalle_pedido(request, pedido_id):
    try:
        cliente = Cliente.objects.get(user=request.user)
    except Cliente.DoesNotExist:
        return redirect('listado_pedidos')
    pedido = get_object_or_404(Pedido, id=pedido_id, cliente=cliente)
    items = ItemPedido.objects.filter(pedido=pedido)
    context = {'pedido': pedido, 'items': items, 'total': pedido.total}
    context.update(_get_carrito_context(request))
    return render(request, 'detalles_pedido.html', context)

@login_required
def crear_pedido_desde_carrito(request):
    """
    Crea un Pedido a partir del Carrito actual
    y redirige al checkout de Stripe.
    """
    carrito = _get_or_create_carrito(request)

    if not carrito or carrito.get_cantidad_items() == 0:
        messages.error(request, "Tu carrito está vacío.")
        return redirect('carrito_compra')

    # Obtener cliente
    try:
        cliente = Cliente.objects.get(user=request.user)
    except Cliente.DoesNotExist:
        messages.error(request, "No tienes un perfil de cliente asociado.")
        return redirect('carrito_compra')

    # Generar número de pedido único "académico"
    numero_pedido = f"PED-{cliente.id}-{int(timezone.now().timestamp())}"

    subtotal = carrito.get_total()
    envio = Decimal("5.00") if subtotal > 0 and subtotal < 50 else Decimal("0.00")
    impuestos = Decimal("0.00")
    descuento = Decimal("0.00")

    # Crear el pedido
    pedido = Pedido.objects.create(
        cliente=cliente,
        numero_pedido=numero_pedido,
        subtotal=subtotal,
        impuestos=impuestos,
        coste_entrega=envio,
        descuento=descuento,
        direccion_envio=getattr(cliente, "direccion", ""),
        telefono=getattr(cliente, "telefono", ""),
    )

    # Pasar los items del carrito al pedido
    for item in carrito.itemcarrito_set.select_related('producto'):
        ItemPedido.objects.create(
            pedido=pedido,
            producto=item.producto,
            talla=item.talla,
            cantidad=item.cantidad,
            precio_unitario=item.producto.precio_final,
        )

    # Vaciar carrito (los productos ya están en el pedido)
    carrito.itemcarrito_set.all().delete()

    # Redirigir al checkout de Stripe
    return redirect('checkout_pedido', numero_pedido=pedido.numero_pedido)