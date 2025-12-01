from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from client.models import Cliente
from product.models import Product
from pedido.models import Pedido, ItemPedido, Carrito
from decimal import Decimal

class SecurityTests(TestCase):
    def setUp(self):
        # Configuración inicial para las pruebas
        self.client = Client()
        
        # 1. Crear Usuarios (Atacante y Víctima)
        self.user_victim = User.objects.create_user(username='victima', password='password123')
        self.cliente_victim, _ = Cliente.objects.get_or_create(user=self.user_victim)
        
        self.user_attacker = User.objects.create_user(username='atacante', password='password123')
        self.cliente_attacker, _ = Cliente.objects.get_or_create(user=self.user_attacker)

        # 2. Crear Producto
        self.product = Product.objects.create(
            nombre='Zapato Test',
            precio=Decimal('50.00'),
            stock=100,
            disponible=True
        )

        # 3. Crear Pedido de la Víctima
        self.pedido_victim = Pedido.objects.create(
            cliente=self.cliente_victim,
            numero_pedido="PED-VICTIMA-001",
            subtotal=Decimal('50.00'),
            estado=Pedido.EstadoPedido.PENDIENTE,
            estado_pago="pendiente"
        )
    
    def test_security_idor_order_detail(self):
        """
        PRUEBA DE SEGURIDAD (IDOR):
        Un atacante logueado NO debería poder ver el detalle del pedido de la víctima.
        """
        self.client.login(username='atacante', password='password123')
        
        # Intentar acceder al pedido de la víctima
        url = reverse('detalle_pedido', args=[self.pedido_victim.id])
        response = self.client.get(url)

        # Si devuelve 200 (OK), es VULNERABLE. Debería ser 404 (No encontrado) o 403 (Prohibido).
        if response.status_code == 200:
            print("\n[FALLO DE SEGURIDAD] IDOR detectado: El atacante pudo ver el pedido de la víctima.")
        
        self.assertNotEqual(response.status_code, 200, "Fallo de seguridad: IDOR permite ver pedidos ajenos.")

    def test_security_payment_bypass(self):
        """
        PRUEBA DE SEGURIDAD (LOGICA DE NEGOCIO):
        Verificar si se puede marcar un pedido como pagado forzando la URL de éxito
        sin pasar por la pasarela de pago.
        """
        # El pedido nace como pendiente
        self.assertEqual(self.pedido_victim.estado_pago, "pendiente")

        # El atacante intenta adivinar la URL de éxito
        url_exito = reverse('pedido_pago_exito', args=[self.pedido_victim.numero_pedido])
        
        # Hacemos GET a la URL de éxito directamente
        self.client.get(url_exito)

        # Refrescamos el objeto desde la BD
        self.pedido_victim.refresh_from_db()

        # Si el estado cambió a pagado solo por visitar la URL, es VULNERABLE
        if self.pedido_victim.estado_pago == "pagado":
            print(f"\n[CRITICO] VULNERABILIDAD DETECTADA: Bypass de pago exitoso en {url_exito}")

        # Esta aserción fallará con tu código actual, revelando el error
        self.assertNotEqual(self.pedido_victim.estado_pago, "pagado", 
            "Fallo crítico: El pedido se marcó como pagado simplemente visitando la URL de éxito.")

    def test_security_negative_inventory(self):
        """
        PRUEBA DE SEGURIDAD (INTEGRIDAD DE DATOS):
        Intentar agregar cantidades negativas al carrito.
        """
        url = reverse('agregar_al_carrito', args=[self.product.id])
        
        # Intentar inyectar cantidad negativa
        data = {'cantidad': -5, 'talla_id': ''} 
        response = self.client.post(url, data)
        
        # Verificar el carrito
        carrito = Carrito.objects.first()
        if carrito:
            items = carrito.itemcarrito_set.all()
            for item in items:
                self.assertTrue(item.cantidad > 0, "Fallo de seguridad: Se permitió una cantidad negativa en el carrito.")
        else:
            # Si no se creó carrito o items, la prueba pasa (fue rechazado)
            pass

    def test_xss_protection_tracking(self):
        """
        PRUEBA DE SEGURIDAD (XSS):
        Intentar inyectar scripts en el formulario de rastreo.
        """
        url = reverse('rastrear_pedido')
        script_malicioso = "<script>alert('hack')</script>"
        
        data = {
            'numero_pedido': script_malicioso,
            'telefono': '123456789'
        }
        
        response = self.client.post(url, data)
        
        # Django escapa automáticamente, pero verificamos que el script no se ejecute
        # Si el script aparece tal cual en el HTML sin escapar, es vulnerable.
        content = response.content.decode('utf-8')
        
        # Verificamos que los caracteres especiales estén escapados (&lt;script&gt;)
        self.assertNotIn(script_malicioso, content, "Posible vulnerabilidad XSS: El script se reflejó sin escapar.")