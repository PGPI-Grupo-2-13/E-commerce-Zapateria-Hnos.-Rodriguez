from django.test import TestCase
from django.urls import reverse
from decimal import Decimal

from .models import Product, Category, Brand, ProductImage


class ProductModelTests(TestCase):
	def setUp(self):
		self.brand = Brand.objects.create(nombre='MarcaTest')
		self.categoria = Category.objects.create(nombre='CatTest')

	def test_precio_final_without_oferta_returns_precio(self):
		p = Product.objects.create(
			nombre='Sin Oferta',
			precio=Decimal('100.00'),
			stock=5,
			disponible=True,
			marca=self.brand,
			categoria=self.categoria
		)
		self.assertEqual(p.precio_final, Decimal('100.00'))

	def test_precio_final_with_oferta_applies_discount(self):
		p = Product.objects.create(
			nombre='Con Oferta',
			precio=Decimal('200.00'),
			oferta=Decimal('25.00'),
			stock=5,
			disponible=True,
			marca=self.brand,
			categoria=self.categoria
		)
		# 25% de 200 = 50 -> precio final 150.00
		self.assertEqual(p.precio_final, Decimal('150.00'))

	def test_imagen_principal_returns_first_principal_or_first(self):
		p = Product.objects.create(
			nombre='Con Imagen',
			precio=Decimal('10.00'),
			stock=2,
			disponible=True,
			marca=self.brand,
			categoria=self.categoria
		)
		# no images -> empty string
		self.assertEqual(p.imagen_principal(), "")

		# add a non-principal image and then a principal
		img1 = ProductImage.objects.create(producto=p, imagen='http://img/1.jpg', es_principal=False)
		self.assertEqual(p.imagen_principal(), 'http://img/1.jpg')

		img2 = ProductImage.objects.create(producto=p, imagen='http://img/2.jpg', es_principal=True)
		# now principal should be img2
		self.assertEqual(p.imagen_principal(), 'http://img/2.jpg')


class ProductViewsTests(TestCase):
	def setUp(self):
		self.brand = Brand.objects.create(nombre='MarcaTest')
		self.categoria = Category.objects.create(nombre='CatTest')

		# two available products in same category
		self.p1 = Product.objects.create(
			nombre='Zapato A',
			precio=Decimal('30.00'),
			stock=5,
			disponible=True,
			marca=self.brand,
			categoria=self.categoria
		)
		self.p2 = Product.objects.create(
			nombre='Zapato B',
			precio=Decimal('40.00'),
			stock=3,
			disponible=True,
			marca=self.brand,
			categoria=self.categoria
		)

	def test_product_list_contains_available_products(self):
		url = reverse('product:product_list')
		response = self.client.get(url)
		self.assertEqual(response.status_code, 200)
		self.assertIn('page_obj', response.context)
		# both products should appear in the queryset
		names = [p.nombre for p in response.context['page_obj'].object_list]
		self.assertIn(self.p1.nombre, names)
		self.assertIn(self.p2.nombre, names)

	def test_product_detail_shows_product_and_related(self):
		url = reverse('product:product_detail', args=[self.p1.slug])
		response = self.client.get(url)
		self.assertEqual(response.status_code, 200)
		self.assertIn('product', response.context)
		self.assertEqual(response.context['product'].id, self.p1.id)
		# related_products should include p2
		related = list(response.context.get('related_products', []))
		related_ids = [r.id for r in related]
		self.assertIn(self.p2.id, related_ids)

