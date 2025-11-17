from django.core.management.base import BaseCommand
from product.models import Category, Brand, Product, ProductSize, ProductImage
from seeder_flag.models import SeederStatus
from faker import Faker
import random

class Command(BaseCommand):
    help = 'Seed the database with sample products'

    def add_arguments(self, parser):
        parser.add_argument('--number', type=int, default=20, help='Number of products to create')

    def handle(self, *args, **options):
        status, created = SeederStatus.objects.get_or_create(name='seed_products')

        if status.executed:
            self.stdout.write(self.style.WARNING('Products already seeded.'))
            return

        fake = Faker('es_ES')
        number = options['number']
        
        self.stdout.write(self.style.WARNING('Creating categories and brands...'))
        
        # Crear categorías
        categorias_nombres = ['Casual', 'Formales', 'Botas']
        categorias = []
        imagenes_categorias = ["https://static.zara.net/assets/public/60f5/a2cd/0df946199286/c5cf289b2858/12290620001-ult31/12290620001-ult31.jpg?ts=1756741117672&w=602",
                               "https://static.zara.net/assets/public/c9f0/900a/fb2c4665be10/ab8afa18ed5c/12401520700-ult31/12401520700-ult31.jpg?ts=1754052849951&w=602",
                               "https://static.zara.net/assets/public/f538/2dd9/35144f78b92f/e8dbb6be3a99/12016720800-ult31/12016720800-ult31.jpg?ts=1761140792257&w=602"]
        for nombre in categorias_nombres:
            cat, created = Category.objects.get_or_create(
                nombre=nombre,
                descripcion= fake.text(max_nb_chars=200),
                imagen= imagenes_categorias[categorias_nombres.index(nombre)]
            )
            categorias.append(cat)
        
        # Crear marcas
        marcas_nombres = ['Zara', 'Massimo Dutti', 'Tommy Hilfiger', 'Martinelli']
        imagenes_marcas = [ "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fd/Zara_Logo.svg/2560px-Zara_Logo.svg.png",
                            "https://r.fashionunited.com/nWvxR2Z7vP9sJeVyII3dQCs_QwmFyLGPSgRzQ9qeHnI/resize:fill:1164:0:0/gravity:ce/quality:70/aHR0cHM6Ly9mYXNoaW9udW5pdGVkLmNvbS9pbWcvdXBsb2FkLzIwMjMvMDYvMDIvbG9nby1tYXNzaW1vLWR1dHRpLWZveXc1a25sLTIwMjMtMDYtMDIucG5n",
                            "https://1000logos.net/wp-content/uploads/2022/08/Tommy-Hilfiger-logo.png",
                            "https://calzadosalcon.es/images/PRO/0211/logo.jpg" ]
        marcas = []
        for nombre in marcas_nombres:
            brand, created = Brand.objects.get_or_create(
                nombre=nombre,
                imagen = imagenes_marcas[marcas_nombres.index(nombre)]
            )
            marcas.append(brand)
        
        self.stdout.write(self.style.WARNING(f'Creating {number} products...'))
        
        colores = ['Negro', 'Blanco', 'Azul', 'Rojo', 'Gris', 'Marrón', 'Verde', 'Beige']
        materiales = ['Cuero', 'Sintético', 'Lona', 'Gamuza', 'Malla', 'Tela']
        tallas = ['36', '37', '38', '39', '40', '41', '42', '43', '44', '45']
        
        for i in range(number):
            # Crear producto
            nombre = f"Zapato {random.randint(100, 999)}"
            producto = Product.objects.create(
                nombre=nombre[:200],
                descripcion=fake.text(max_nb_chars=500),
                precio=round(random.uniform(29.99, 199.99), 2),
                oferta=random.choice([None, None, None, 10, 15, 20, 25, 30]),  # 30% con oferta
                genero=random.choice(['U', 'M', 'F', 'K']),
                color=random.choice(colores)[:80],
                material=random.choice(materiales)[:120],
                stock=random.randint(0, 100),
                disponible=random.choice([True, True, True, False]),  # 75% disponible
                destacado=random.choice([True, False, False, False]),  # 25% destacado
                categoria=random.choice(categorias),
                marca=random.choice(marcas)
            )
            
            # Crear tallas para el producto
            for talla in tallas:
                ProductSize.objects.create(
                    producto=producto,
                    talla=talla,
                    stock=random.randint(0, 20)
                )
            
            # Crear imágenes para el producto
            imagenes = ["https://static.zara.net/assets/public/fc8a/0e3a/33a4441e8c46/b302c911c308/12401522800-ult30/12401522800-ult30.jpg?ts=1753778636155&w=602", 
                        "https://static.zara.net/assets/public/c9f0/900a/fb2c4665be10/ab8afa18ed5c/12401520700-ult31/12401520700-ult31.jpg?ts=1754052849951&w=602", 
                        "https://static.zara.net/assets/public/cef9/d8c8/79984de482a4/7fc8df1f2a86/12415620700-e1/12415620700-e1.jpg?ts=1757488507451&w=602", 
                        "https://static.zara.net/assets/public/e161/eb14/47874a238f58/991382b61d03/12402620700-ult30/12402620700-ult30.jpg?ts=1753441823957&w=602", 
                        "https://static.zara.net/assets/public/4857/6a63/12b343809f7f/0fe655c8b879/12403720800-e1/12403720800-e1.jpg?ts=1760626813507&w=602",
                        "https://static.zara.net/assets/public/9f51/4f49/2ac345f1b932/ff93c3ba9572/12408620131-ult30/12408620131-ult30.jpg?ts=1753710223354&w=602",
                        "https://static.zara.net/assets/public/3436/4d7b/2c9d4c4ab297/195c8db07a55/12433620800-ult30/12433620800-ult30.jpg?ts=1753441948673&w=602",
                        "https://static.zara.net/assets/public/b02a/4fac/c40049f5a4f7/709952796c1c/12404620800-ult30/12404620800-ult30.jpg?ts=1753441825330&w=602",
                        "https://static.zara.net/assets/public/6f7b/b99f/929042c1aefc/accf7e2114c6/12433620131-ult30/12433620131-ult30.jpg?ts=1753441943735&w=602",
                        "https://static.zara.net/assets/public/53f3/9ac3/7dc94a55a1c2/9ec699f80823/12403620800-ult30/12403620800-ult30.jpg?ts=1753441825095&w=602",
                        "https://static.zara.net/assets/public/6189/10c1/a2554bef950f/9a026be4d59e/12008620800-e1/12008620800-e1.jpg?ts=1759305829620&w=602",
                        "https://static.zara.net/assets/public/84fe/ae60/5ad949beafeb/615e2fb37105/12002620800-e1/12002620800-e1.jpg?ts=1755513360047&w=602",]
            
            ProductImage.objects.create(
                producto=producto,
                imagen=random.choice(imagenes),
                es_principal=True,
            )

        status.executed = True
        status.save()

        self.stdout.write(self.style.SUCCESS(f'Created {len(categorias)} categories'))
        self.stdout.write(self.style.SUCCESS(f'Created {len(marcas)} brands'))
        self.stdout.write(self.style.SUCCESS(f'Successfully created {number} products!'))

