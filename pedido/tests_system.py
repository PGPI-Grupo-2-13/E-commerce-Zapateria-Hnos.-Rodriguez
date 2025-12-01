from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from product.models import Product
from pedido.models import Pedido, ItemPedido, Carrito
from decimal import Decimal

class SystemPurchaseTest(TestCase):
    def setUp(self):
        # 1. Preparar el entorno (Cliente y Producto)
        self.client = Client()
        self.user = User.objects.create_user(username='comprador', email='test@test.com', password='password123')
        
        # Producto con stock suficiente
        self.producto = Product.objects.create(
            nombre='Mocasines Test',
            precio=Decimal('80.00'),
            stock=10,
            disponible=True
        )

    def test_full_purchase_flow_authenticated(self):
        """
        SIMULACIÓN DE SISTEMA COMPLETA:
        Usuario se loguea -> Añade al carrito -> Rellena checkout -> Se crea el pedido.
        """
        # PASO 1: Login
        login_success = self.client.login(username='comprador', password='password123')
        self.assertTrue(login_success, "El login falló al inicio de la prueba de sistema.")

        # PASO 2: Añadir producto al carrito
        url_add = reverse('agregar_al_carrito', args=[self.producto.id])
        self.client.post(url_add, {'cantidad': 2, 'redirect_to_cart': '1'})
        
        # Verificación intermedia: El carrito debe tener 2 items
        carrito = Carrito.objects.get(cliente__user=self.user)
        self.assertEqual(carrito.get_cantidad_items(), 2)

        # PASO 3: Ir al Checkout (Confirmar Pedido)
        url_checkout = reverse('crear_pedido')
        
        # Datos del formulario de envío (simulando lo que el usuario escribe)
        datos_envio = {
            'nombre': 'Juan',
            'apellidos': 'Pérez',
            'email': 'juan@test.com',
            'direccion': 'Calle Gran Vía 1',
            'ciudad': 'Madrid',
            'codigo_postal': '28013',
            'telefono': '600123456'
        }

        # Hacemos POST (pulsar "Confirmar y Pagar")
        response = self.client.post(url_checkout, datos_envio, follow=True)

        # PASO 4: Verificaciones Finales del Sistema
        
        # A) ¿Se creó el pedido en la base de datos?
        pedido = Pedido.objects.filter(cliente__user=self.user).last()
        self.assertIsNotNone(pedido, "CRÍTICO: El pedido no se guardó en la base de datos.")
        
        # B) ¿El pedido tiene los datos correctos?
        self.assertEqual(pedido.telefono, '600123456')
        self.assertIn('Calle Gran Vía 1', pedido.direccion_envio)
        
        # C) ¿Se guardaron los items del pedido correctamente?
        item_pedido = ItemPedido.objects.get(pedido=pedido)
        self.assertEqual(item_pedido.producto, self.producto)
        self.assertEqual(item_pedido.cantidad, 2)
        self.assertEqual(item_pedido.precio_unitario, Decimal('80.00'))

        # D) ¿El carrito se vació después de la compra?
        # Recargamos el carrito desde la DB
        carrito.refresh_from_db() 
        self.assertEqual(carrito.itemcarrito_set.count(), 0, "El carrito no se vació tras crear el pedido.")

        # E) ¿Redirigió a la pasarela de pago?
        # La URL final debe ser algo como /pedidos/checkout/PED-X-XXXX/
        self.assertIn(f'/pedidos/checkout/{pedido.numero_pedido}/', response.request['PATH_INFO'])

    def test_guest_purchase_flow(self):
        """
        PRUEBA DE SISTEMA (INVITADO):
        Compra sin registrarse.
        """
        # No hacemos login
        
        # 1. Añadir al carrito (se crea carrito de sesión anónima)
        url_add = reverse('agregar_al_carrito', args=[self.producto.id])
        self.client.post(url_add, {'cantidad': 1})

        # 2. Checkout con datos de invitado
        url_checkout = reverse('crear_pedido')
        datos_envio = {
            'nombre': 'Invitado',
            'apellidos': 'Test',
            'email': 'invitado@test.com',
            'direccion': 'Calle Falsa 123',
            'ciudad': 'Sevilla',
            'codigo_postal': '41001',
            'telefono': '777777777'
        }
        
        self.client.post(url_checkout, datos_envio)

        # 3. Verificar que se creó un pedido asociado a un usuario anónimo generado
        # Buscamos por el teléfono que acabamos de meter
        pedido = Pedido.objects.filter(telefono='777777777').first()
        self.assertIsNotNone(pedido, "El sistema falló en la compra de invitado.")
        self.assertEqual(pedido.cliente.user.username.startswith('anonimo_'), True)