# Create your models here.
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from decimal import Decimal


class Category(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    descripcion = models.TextField(blank=True)
    imagen = models.CharField(max_length=500, blank=True, help_text='URL de la imagen')
    slug = models.SlugField(max_length=140, unique=True, blank=True)

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class Brand(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    imagen = models.CharField(max_length=500, blank=True, help_text='URL de la imagen')
    slug = models.SlugField(max_length=140, unique=True, blank=True)

    class Meta:
        verbose_name = "Marca"
        verbose_name_plural = "Marcas"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class Product(models.Model):
    GENDER_CHOICES = (
        ('U', 'Unisex'),
        ('M', 'Hombre'),
        ('F', 'Mujer'),
        ('K', 'Niño/a'),
    )

    nombre = models.CharField(max_length=200)
    slug = models.SlugField(max_length=240, unique=True, blank=True)
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    oferta = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                                 help_text='Descuento en porcentaje (ej: 10 = 10%)')
    genero = models.CharField(max_length=1, choices=GENDER_CHOICES, default='U')
    color = models.CharField(max_length=80, blank=True)
    material = models.CharField(max_length=120, blank=True)
    stock = models.PositiveIntegerField(default=0)
    disponible = models.BooleanField(default=True)
    destacado = models.BooleanField(default=False)
    creado = models.DateTimeField(default=timezone.now)
    modificado = models.DateTimeField(auto_now=True)

    categoria = models.ForeignKey(Category, related_name='productos', on_delete=models.SET_NULL, null=True, blank=True)
    marca = models.ForeignKey(Brand, related_name='productos', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ('-creado',)
        verbose_name = "Producto"
        verbose_name_plural = "Productos"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)[:240]
        super().save(*args, **kwargs)

    @property
    def precio_final(self):
        if self.oferta:
            descuento = (self.oferta / Decimal('100')) * self.precio
            return (self.precio - descuento).quantize(Decimal('0.01'))
        return self.precio

    def imagen_principal(self):
        img = self.imagenes.filter(es_principal=True).first()
        if img:
            return img.imagen
        img = self.imagenes.first()
        if img:
            return img.imagen
        return ""

    def __str__(self):
        return self.nombre


class ProductSize(models.Model):
    producto = models.ForeignKey(Product, related_name='tallas', on_delete=models.CASCADE)
    talla = models.CharField(max_length=50)
    stock = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Talla de producto"
        verbose_name_plural = "Tallas de producto"
        unique_together = ('producto', 'talla')

    def __str__(self):
        return f"{self.producto.nombre} - {self.talla}"


class ProductImage(models.Model):
    producto = models.ForeignKey(Product, related_name='imagenes', on_delete=models.CASCADE)
    imagen = models.CharField(max_length=500, help_text='URL de la imagen')
    es_principal = models.BooleanField(default=False)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Imagen de producto"
        verbose_name_plural = "Imágenes de producto"
        ordering = ('orden',)

    def __str__(self):
        return f"Imagen {self.producto.nombre} ({'principal' if self.es_principal else 'secundaria'})"