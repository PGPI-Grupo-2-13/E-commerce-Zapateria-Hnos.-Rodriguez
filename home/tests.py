from django.test import TestCase
from django.urls import reverse
from decimal import Decimal

from product.models import Product, Brand


class HomeViewTests(TestCase):
	def setUp(self):
		# Create a brand to avoid related lookup errors in template
		self.brand = Brand.objects.create(nombre='MarcaTest')

		# Create products: 3 available, 1 unavailable
		for i in range(3):
			Product.objects.create(
				nombre=f'Producto {i+1}',
				precio=Decimal('19.99'),
				stock=10,
				disponible=True,
				marca=self.brand
			)

		Product.objects.create(
			nombre='Producto No Disponible',
			precio=Decimal('29.99'),
			stock=0,
			disponible=False,
			marca=self.brand
		)

	def test_home_renders_and_includes_productos_destacados(self):
		url = reverse('home')
		response = self.client.get(url)
		self.assertEqual(response.status_code, 200)
		self.assertTemplateUsed(response, 'home.html')
		# context must contain productos_destacados and only available products
		self.assertIn('productos_destacados', response.context)
		productos = response.context['productos_destacados']
		# should be at most 3 (the view slices to 3)
		self.assertLessEqual(len(productos), 3)
		for p in productos:
			self.assertTrue(p.disponible)

	def test_home_shows_empty_message_when_no_destacados(self):
		# Remove all available products
		Product.objects.filter(disponible=True).delete()
		url = reverse('home')
		response = self.client.get(url)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'No hay productos destacados disponibles')

