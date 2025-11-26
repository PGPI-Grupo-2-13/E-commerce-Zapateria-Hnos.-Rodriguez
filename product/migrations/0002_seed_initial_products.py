from django.db import migrations


def crear_datos_iniciales(apps, schema_editor):
    Category = apps.get_model('product', 'Category')
    Brand = apps.get_model('product', 'Brand')
    Product = apps.get_model('product', 'Product')
    ProductImage = apps.get_model('product', 'ProductImage')
    ProductSize = apps.get_model('product', 'ProductSize')

    # ------------------------------
    # 1) Crear Categorías (con slug explícito)
    # ------------------------------
    cat_calzado, _ = Category.objects.get_or_create(
        slug="calzado",
        defaults={
            "nombre": "Calzado",
            "descripcion": "Todo tipo de calzado",
            "imagen": "",
        }
    )

    cat_deportivo, _ = Category.objects.get_or_create(
        slug="deportivo",
        defaults={
            "nombre": "Deportivo",
            "descripcion": "Zapatillas deportivas",
            "imagen": "",
        }
    )

    # ------------------------------
    # 2) Crear Marcas (con slug explícito)
    # ------------------------------
    brand_nike, _ = Brand.objects.get_or_create(
        slug="nike",
        defaults={
            "nombre": "Nike",
            "imagen": "",
        }
    )

    brand_adidas, _ = Brand.objects.get_or_create(
        slug="adidas",
        defaults={
            "nombre": "Adidas",
            "imagen": "",
        }
    )

    # ------------------------------
    # 3) Crear Productos
    # ------------------------------
    productos_data = [
        {
            "nombre": "Zapatillas Nike Classic",
            "slug": "zapatillas-nike-classic",
            "descripcion": "Modelo clásico de Nike, cómodo y versátil.",
            "precio": 59.99,
            "oferta": None,
            "genero": "U",
            "color": "Blanco",
            "material": "Sintético",
            "stock": 30,
            "categoria": cat_calzado,
            "marca": brand_nike,
            "imagenes": [
                "https://example.com/nike1.jpg",
                "https://example.com/nike2.jpg"
            ],
            "tallas": ["40", "41", "42", "43"]
        },
        {
            "nombre": "Adidas Run Pro",
            "slug": "adidas-run-pro",
            "descripcion": "Zapatilla ideal para running.",
            "precio": 79.99,
            "oferta": 10,  # 10% descuento
            "genero": "M",
            "color": "Negro",
            "material": "Malla transpirable",
            "stock": 25,
            "categoria": cat_deportivo,
            "marca": brand_adidas,
            "imagenes": [
                "https://example.com/adidas1.jpg",
                "https://example.com/adidas2.jpg"
            ],
            "tallas": ["41", "42", "44"]
        },
        {
            "nombre": "Botas de Montaña Pro",
            "slug": "botas-montana-pro",
            "descripcion": "Botas resistentes para senderismo.",
            "precio": 89.99,
            "oferta": None,
            "genero": "U",
            "color": "Marrón",
            "material": "Cuero",
            "stock": 15,
            "categoria": cat_calzado,
            "marca": brand_nike,
            "imagenes": [
                "https://example.com/montana1.jpg"
            ],
            "tallas": ["42", "43", "44", "45"]
        }
    ]

    for pdata in productos_data:
        producto, _ = Product.objects.get_or_create(
            slug=pdata["slug"],
            defaults={
                "nombre": pdata["nombre"],
                "descripcion": pdata["descripcion"],
                "precio": pdata["precio"],
                "oferta": pdata["oferta"],
                "genero": pdata["genero"],
                "color": pdata["color"],
                "material": pdata["material"],
                "stock": pdata["stock"],
                "categoria": pdata["categoria"],
                "marca": pdata["marca"],
            }
        )

        # 4) Imágenes
        for i, url in enumerate(pdata["imagenes"]):
            ProductImage.objects.get_or_create(
                producto=producto,
                orden=i,
                defaults={
                    "imagen": url,
                    "es_principal": (i == 0),
                }
            )

        # 5) Tallas
        for talla in pdata["tallas"]:
            ProductSize.objects.get_or_create(
                producto=producto,
                talla=talla,
                defaults={"stock": 5},
            )


def eliminar_datos_iniciales(apps, schema_editor):
    Product = apps.get_model('product', 'Product')
    slugs = [
        "zapatillas-nike-classic",
        "adidas-run-pro",
        "botas-montana-pro",
    ]
    Product.objects.filter(slug__in=slugs).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(crear_datos_iniciales, eliminar_datos_iniciales),
    ]
