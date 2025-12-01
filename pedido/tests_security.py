from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from client.models import Cliente
from product.models import Product
from pedido.models import Pedido, ItemPedido, Carrito, ItemCarrito
from decimal import Decimal
from pedido import views
import re

class SecurityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_victim = User.objects.create_user(username='victima', password='password123')
        self.cliente_victim, _ = Cliente.objects.get_or_create(user=self.user_victim)
        
        self.user_attacker = User.objects.create_user(username='atacante', password='password123')
        self.cliente_attacker, _ = Cliente.objects.get_or_create(user=self.user_attacker)

        self.product = Product.objects.create(
            nombre='Zapato Test',
            precio=Decimal('50.00'),
            stock=100,
            disponible=True
        )

        self.pedido_victim = Pedido.objects.create(
            cliente=self.cliente_victim,
            numero_pedido="PED-VICTIMA-001",
            subtotal=Decimal('50.00'),
            estado=Pedido.EstadoPedido.PENDIENTE,
            estado_pago="pendiente"
        )
    
    def test_security_idor_order_detail(self):
        self.client.login(username='atacante', password='password123')
        url = reverse('detalle_pedido', args=[self.pedido_victim.id])
        response = self.client.get(url)
        self.assertNotEqual(response.status_code, 200)

    def test_security_payment_bypass(self):
        url_exito = reverse('pedido_pago_exito', args=[self.pedido_victim.numero_pedido])
        self.client.get(url_exito)
        self.pedido_victim.refresh_from_db()
        self.assertNotEqual(self.pedido_victim.estado_pago, "pagado")

    def test_security_negative_inventory(self):
        url = reverse('agregar_al_carrito', args=[self.product.id])
        data = {'cantidad': -5, 'talla_id': ''} 
        self.client.post(url, data)
        carrito = Carrito.objects.first()
        if carrito:
            items = carrito.itemcarrito_set.all()
            for item in items:
                self.assertTrue(item.cantidad > 0)

    def test_xss_protection_tracking(self):
        url = reverse('rastrear_pedido')
        script_malicioso = "<script>alert('hack')</script>"
        data = {
            'numero_pedido': script_malicioso,
            'telefono': '123456789'
        }
        response = self.client.post(url, data)
        content = response.content.decode('utf-8')
        self.assertNotIn(script_malicioso, content)

class AdvancedSecurityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.product = Product.objects.create(
            nombre='Zapato Test', precio=Decimal('50.00'), stock=10, disponible=True
        )
        self.cliente, _ = Cliente.objects.get_or_create(user=self.user)
        self.pedido = Pedido.objects.create(
            cliente=self.cliente, numero_pedido="PED-TEST-001", 
            subtotal=Decimal('50.00')
        )

    def test_security_unauthenticated_crash(self):
        self.client.logout()
        url = reverse('detalle_pedido', args=[self.pedido.id])
        try:
            response = self.client.get(url)
        except TypeError:
            self.fail()
        self.assertNotEqual(response.status_code, 500)

    def test_security_csrf_protection(self):
        self.client.login(username='testuser', password='password123')
        url = reverse('agregar_al_carrito', args=[self.product.id])
        self.assertFalse(hasattr(views.agregar_al_carrito, 'csrf_exempt'))

class ExtraSecurityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='usuario_test', email='test@test.com', password='password123')
        self.cliente, _ = Cliente.objects.get_or_create(user=self.user)
        self.producto = Product.objects.create(
            nombre="Producto Test", 
            precio=Decimal("100.00"), 
            stock=50, 
            disponible=True
        )

    def test_security_open_redirect_login(self):
        url_login = reverse('client-login')
        phishing_url = "http://malicious-site.com/login"
        response = self.client.post(f"{url_login}?next={phishing_url}", {
            'username': 'usuario_test',
            'password': 'password123'
        })
        self.assertNotEqual(response.url, phishing_url)
        self.assertTrue(response.url.startswith('/') or 'http' not in response.url)

    def test_security_user_enumeration(self):
        url_login = reverse('client-login')
        
        username_no_exist = 'usuario_fantasma@test.com'
        username_exist = 'usuario_test'

        response_no_exist = self.client.post(url_login, {
            'username': username_no_exist,
            'password': 'password123'
        })
        
        response_wrong_pass = self.client.post(url_login, {
            'username': username_exist,
            'password': 'password_incorrecta'
        })

        csrf_pattern = re.compile(rb'<input type="hidden" name="csrfmiddlewaretoken" value="[^"]+">')
        
        content_no_exist = csrf_pattern.sub(b'', response_no_exist.content)
        content_wrong_pass = csrf_pattern.sub(b'', response_wrong_pass.content)
        content_no_exist = content_no_exist.replace(username_no_exist.encode(), b'USER_PLACEHOLDER')
        content_wrong_pass = content_wrong_pass.replace(username_exist.encode(), b'USER_PLACEHOLDER')
        
        self.assertEqual(content_no_exist, content_wrong_pass)

    def test_security_admin_access_control(self):
        self.client.login(username='usuario_test', password='password123')
        response = self.client.get('/admin/')
        self.assertNotEqual(response.status_code, 200)

    def test_security_xss_search(self):
        url_catalogo = reverse('product:product_list')
        payload = '<script>alert("XSS")</script>'
        response = self.client.get(url_catalogo, {'search': payload})
        content = response.content.decode('utf-8')
        self.assertIn('&lt;script&gt;alert(&quot;XSS&quot;)&lt;/script&gt;', content)
        self.assertNotIn(payload, content)

    def test_security_price_tampering_checkout(self):
        self.client.login(username='usuario_test', password='password123')
        carrito = Carrito.objects.create(cliente=self.cliente)
        ItemCarrito.objects.create(carrito=carrito, producto=self.producto, cantidad=1)
        url_checkout = reverse('crear_pedido')
        datos_form = {
            'nombre': 'Hacker',
            'apellidos': 'Test',
            'email': 'hacker@test.com',
            'direccion': 'Calle Falsa 123',
            'ciudad': 'Madrid',
            'codigo_postal': '28000',
            'telefono': '600000000',
            'subtotal': '1.00', 
            'total': '1.00',
            'precio': '1.00'
        }
        self.client.post(url_checkout, datos_form)
        ultimo_pedido = Pedido.objects.filter(cliente=self.cliente).last() 
        self.assertIsNotNone(ultimo_pedido) 
        self.assertEqual(ultimo_pedido.subtotal, Decimal("100.00"))