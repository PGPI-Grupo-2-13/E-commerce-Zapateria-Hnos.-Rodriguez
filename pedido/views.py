from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse 
from django.conf import settings
from decimal import Decimal
from django.utils import timezone
from django.db.models import F  
from django.core.mail import send_mail
from django.template.loader import render_to_string
from threading import Thread

from .forms import CheckoutForm, OrderTrackingForm
from django.contrib.auth.models import User
from .models import Pedido, ItemPedido, Carrito, ItemCarrito
from client.models import Cliente
from product.models import Product, ProductSize
from .stripe_api import create_payment_intent
import uuid, stripe
try:
    import resend
except Exception:
    resend = None


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
        try:
            cliente = Cliente.objects.get(user=request.user) 
        except Cliente.DoesNotExist:
            cliente = Cliente.objects.create(user=request.user, direccion='', ciudad='', codigo_postal='') 
        
        qs = Carrito.objects.filter(cliente=cliente)
        
        if qs.exists():
            carrito = qs.first()
            if qs.count() > 1:
                for duplicado in qs[1:]:
                    duplicado.delete()
        else:
            carrito = Carrito.objects.create(cliente=cliente, session_key=None)
        
        if carrito.session_key:
            carrito.session_key = None
            carrito.save()

    else:
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

def enviar_correo_confirmacion_pedido(pedido):
    """
    Envía un correo de confirmación al cliente cuando se completa el pago.
    """
    try:
        # Obtener el email del cliente
        email_cliente = pedido.cliente.user.email 
        
        # Si el cliente no tiene email, intentar obtenerlo del formulario
        # o usar un email por defecto
        if not email_cliente:
            # Si es un usuario invitado, no podemos enviar correo
            if pedido.cliente.user.username == "invitado_anonimo":
                print(f"[Email] No se puede enviar correo: cliente invitado sin email")
                return False
            email_cliente = pedido.cliente.user.email
        
        if not email_cliente:
            print(f"[Email] No se puede enviar correo: cliente sin email configurado")
            return False
        
        # Obtener los items del pedido
        items = pedido.items.all()
        
        # Renderizar el template del correo
        html_message = render_to_string('confirmacion_pedido.html', {
            'pedido': pedido,
            'items': items,
        })
        
        # Asunto del correo
        subject = f'Confirmación de Pedido #{pedido.numero_pedido} - Zapatería Hnos. Rodríguez'
        
        def _tarea_envio():
            """Ejecuta el envío real fuera del hilo principal."""
            try:
                if resend is None:
                    print("[Resend] Paquete 'resend' no instalado; omitiendo envío de correo en entorno de pruebas.")
                    return

                # Configurar API Key
                resend.api_key = settings.RESEND_API_KEY

                # REMITENTE: Obligatorio usar este si no tienes dominio
                remitente_seguro = "onboarding@resend.dev"

                # En un proyecto real aquí iría [email_cliente].
                destinatario_seguro = ["pgpi-2-13@outlook.es"]

                print(f"[Demo Uni] Redirigiendo correo de {email_cliente} a {destinatario_seguro} para demostración.")

                params = {
                    "from": remitente_seguro,
                    "to": destinatario_seguro,
                    "subject": subject,
                    "html": html_message,
                }

                email = resend.Emails.send(params)
                print(f"[Resend] Correo enviado con éxito. ID: {email.get('id')}")

            except Exception as e:
                print(f"[Resend] Error al enviar correo: {str(e)}")
        
        Thread(target=_tarea_envio, daemon=True).start()
        return True
        
    except Exception as e:
        print(f"[Email] Error al enviar correo: {str(e)}")
        return False

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

        if stock_valido and unidades_a_restar > 0:
            stock_object.stock -= unidades_a_restar
            stock_object.save()
        
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
        msg = f'Stock insuficiente. Máximo: {stock_disponible_real}'
        if _is_ajax(request): return JsonResponse({'success': False, 'message': msg, 'max_qty': stock_disponible_real}, status=400)
        messages.error(request, msg)
        
    else:
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
        
        try:
            item = ItemCarrito.objects.select_related('producto').get(id=item_id, carrito=carrito) 
        except ItemCarrito.DoesNotExist:
            if _is_ajax(request):
                return JsonResponse({'success': True, 'message': 'El producto ya no estaba en el carrito.'})
            messages.warning(request, 'El producto ya no se encuentra en el carrito.')
            return redirect('carrito_compra')
            
        nombre_producto = item.producto.nombre
        cantidad_a_devolver = item.cantidad

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

        if _is_ajax(request):
            return JsonResponse({'success': True, 'message': f'{nombre_producto} eliminado.'})
            
        messages.success(request, f'"{nombre_producto}" eliminado del carrito.')
        return redirect('carrito_compra')
    
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
    envio = Decimal('5.00') if Decimal('0') < subtotal < Decimal('50') else Decimal('0')
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

    if pedido.estado_pago == "pagado":
        return redirect("pedido_pago_exito", numero_pedido=numero_pedido)

    if not pedido.stripe_payment_intent_id:
        payment_intent = create_payment_intent(pedido)

        if payment_intent is None:
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
    pedido = get_object_or_404(Pedido, numero_pedido=numero_pedido)

    if pedido.stripe_payment_intent_id:
        try:
            intent = stripe.PaymentIntent.retrieve(pedido.stripe_payment_intent_id)
            if intent.status == 'succeeded':
                pedido.estado_pago = "pagado"
                pedido.estado = Pedido.EstadoPedido.PAGADO
                pedido.save()
                return render(request, "pago_exito.html", {"pedido": pedido})
        except stripe.error.StripeError:
            pass 
    
    return redirect('pedido_pago_error', numero_pedido=numero_pedido)


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
    if not request.user.is_authenticated:
        messages.info(request, "Como invitado no tienes un historial de pedidos. Revisa tu correo para ver el detalle.")
        return redirect('product:product_list')
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
    
    items = ItemPedido.objects.filter(pedido=pedido).annotate(
        subtotal_item=F('cantidad') * F('precio_unitario')
    )
    
    context = {'pedido': pedido, 'items': items, 'total': pedido.total}
    context.update(_get_carrito_context(request))
    return render(request, 'detalles_pedido.html', context)

# Modifica esta función para manejar el Cliente que ya fue creado por el signal
def _get_cliente_invitado(datos_formulario):
    if datos_formulario:
        # Crear usuario anónimo único con los datos del formulario
        timestamp = int(timezone.now().timestamp())
        unique_id = str(uuid.uuid4())[:8]
        username = f"anonimo_{timestamp}_{unique_id}"
        
        user = User.objects.create_user(
            username=username,
            email=datos_formulario.get('email', ''),
            first_name=datos_formulario.get('nombre', ''),
            last_name=datos_formulario.get('apellidos', ''),
            password=None
        )
        user.set_unusable_password()
        user.save()
        
        # El signal ya creó el Cliente, solo necesitamos obtenerlo y actualizarlo
        cliente = Cliente.objects.get(user=user)
        # Actualizamos los datos del cliente con los del formulario
        cliente.direccion = datos_formulario.get('direccion', '')
        cliente.ciudad = datos_formulario.get('ciudad', '')
        cliente.codigo_postal = datos_formulario.get('codigo_postal', '')
        cliente.telefono = datos_formulario.get('telefono', '')
        cliente.save()
    else:
        # Comportamiento por defecto (por si acaso se usa en otro lugar)
        user, created = User.objects.get_or_create(
            username="invitado_anonimo",
            defaults={
                'first_name': 'Cliente', 'last_name': 'Invitado', 'email': 'invitado@tienda.com'
            }
        )
        if created:
            user.set_unusable_password()
            user.save()
        cliente, _ = Cliente.objects.get_or_create(user=user)
    
    return cliente

def crear_pedido_desde_carrito(request):
    """
    1. Muestra formulario de datos.
    2. Recibe datos, asigna usuario (real o invitado) y crea el pedido.
    """
    carrito = _get_or_create_carrito(request)

    if not carrito or carrito.get_cantidad_items() == 0:
        messages.error(request, "Tu carrito está vacío.")
        return redirect('carrito_compra')

    initial_data = {}
    if request.user.is_authenticated:
        try:
            cliente = Cliente.objects.get(user=request.user)
            initial_data = {
                'nombre': request.user.first_name or '',
                'apellidos': request.user.last_name or '',
                'direccion': getattr(cliente, 'direccion', ''),
                'ciudad': getattr(cliente, 'ciudad', ''),
                'codigo_postal': getattr(cliente, 'codigo_postal', ''),
                'telefono': getattr(cliente, 'telefono', ''),
                'email': request.user.email or '',
            }
        except Cliente.DoesNotExist:
            initial_data = {
                'nombre': request.user.first_name or '',
                'apellidos': request.user.last_name or '',
                'email': request.user.email or '',
            }

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            datos = form.cleaned_data
            direccion_completa = f"{datos['direccion']}, {datos['ciudad']}, {datos['codigo_postal']}"
            telefono = datos['telefono']

            if request.user.is_authenticated:
                try:
                    cliente_pedido = Cliente.objects.get(user=request.user)
                    # Actualizamos los datos del cliente si el usuario los cambió
                    cliente_pedido.direccion = datos['direccion']
                    cliente_pedido.ciudad = datos['ciudad']
                    cliente_pedido.codigo_postal = datos['codigo_postal']
                    cliente_pedido.telefono = datos['telefono']
                    cliente_pedido.save()
                    
                    # Actualizamos también el User si cambió nombre/apellidos/email
                    if datos.get('nombre'):
                        request.user.first_name = datos['nombre']
                    if datos.get('apellidos'):
                        request.user.last_name = datos['apellidos']
                    if datos.get('email'):
                        request.user.email = datos['email']
                    request.user.save()
                except Cliente.DoesNotExist:
                    messages.error(request, "Error con tu usuario.")
                    return redirect('carrito_compra')
            else:
                # Pasamos los datos del formulario a la función
                cliente_pedido = _get_cliente_invitado(datos)

            numero_pedido = f"PED-{cliente_pedido.id}-{int(timezone.now().timestamp())}"
            subtotal = carrito.get_total()
            envio = Decimal("5.00") if subtotal > 0 and subtotal < 50 else Decimal("0.00")
            
            pedido = Pedido.objects.create(
                cliente=cliente_pedido,
                numero_pedido=numero_pedido,
                subtotal=subtotal,
                impuestos=Decimal("0.00"),
                coste_entrega=envio,
                descuento=Decimal("0.00"),
                direccion_envio=direccion_completa,
                telefono=telefono,
            )

            for item in carrito.itemcarrito_set.select_related('producto'):
                ItemPedido.objects.create(
                    pedido=pedido,
                    producto=item.producto,
                    talla=item.talla,
                    cantidad=item.cantidad,
                    precio_unitario=item.producto.precio_final,
                )

            carrito.itemcarrito_set.all().delete()

            return redirect('checkout_pedido', numero_pedido=pedido.numero_pedido)
    else:
        form = CheckoutForm(initial=initial_data)

    return render(request, 'checkout_datos.html', {
        'form': form, 
        'carrito': carrito
    })

def rastrear_pedido(request):
    if request.method == 'POST':
        form = OrderTrackingForm(request.POST)
        if form.is_valid():
            numero_pedido = form.cleaned_data['numero_pedido']
            telefono = form.cleaned_data['telefono']
            
            pedido = Pedido.objects.filter(
                numero_pedido=numero_pedido, 
                telefono=telefono
            ).first()

            if pedido:
                items = ItemPedido.objects.filter(pedido=pedido).annotate(
                    subtotal_item=F('cantidad') * F('precio_unitario')
                )
                context = {
                    'pedido': pedido, 
                    'items': items, 
                    'total': pedido.total
                }
                context.update(_get_carrito_context(request))
                return render(request, 'detalles_pedido.html', context)
            else:
                messages.error(request, "No encontramos un pedido con ese número y teléfono.")
    else:
        form = OrderTrackingForm()

    context = {'form': form}
    context.update(_get_carrito_context(request))
    return render(request, 'rastrear_pedido.html', context)