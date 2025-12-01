from django.test import TestCase
from django.urls import reverse
from decimal import Decimal

from django.contrib.auth.models import User

from product.models import Product
from pedido.models import Carrito, ItemCarrito


class PedidoModelAndViewTests(TestCase):
	def setUp(self):
		# create a user (signal will create Cliente)
		self.user = User.objects.create_user(username='cliente1', password='testpass')

		# Create a product with stock
		self.product = Product.objects.create(
			nombre='Zapato Test',
			precio=Decimal('50.00'),
			stock=10,
			disponible=True
		)

	def test_carrito_get_total_and_quantity(self):
		# Create a carrito for the user
		carrito = Carrito.objects.create(cliente=self.user.cliente, session_key=None)

		# Add two items of the product
		ItemCarrito.objects.create(carrito=carrito, producto=self.product, cantidad=2)

		# precio_final should equal precio when oferta is None
		expected_total = self.product.precio_final * 2
		self.assertEqual(carrito.get_total(), expected_total)
		self.assertEqual(carrito.get_cantidad_items(), 2)

	def test_agregar_al_carrito_creates_item_and_reduces_stock(self):
		# Ensure session exists for anonymous carrito
		session = self.client.session
		session.save()
		session_key = session.session_key

		url = reverse('agregar_al_carrito', args=[self.product.id])

		# POST(quantity=3) and ask to redirect to cart
		response = self.client.post(url, {'cantidad': '3', 'redirect_to_cart': '1'})

		# should redirect to carrito view
		self.assertEqual(response.status_code, 302)

		# There should be a carrito linked to the session
		carrito = Carrito.objects.filter(session_key=session_key).first()
		self.assertIsNotNone(carrito)

		item = ItemCarrito.objects.filter(carrito=carrito, producto=self.product).first()
		self.assertIsNotNone(item)
		self.assertEqual(item.cantidad, 3)

		# Product stock should be reduced
		self.product.refresh_from_db()
		self.assertEqual(self.product.stock, 7)

