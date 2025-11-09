# Register your models here.

from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Brand, Product, ProductSize, ProductImage


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('imagen', 'es_principal', 'orden')

    def preview(self, obj):
        if obj.imagen:
            return format_html('<img src="{}" style="height:60px;"/>', obj.imagen.url)
        return ""
    preview.short_description = "Vista"


class ProductSizeInline(admin.TabularInline):
    model = ProductSize
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'marca', 'precio', 'stock', 'disponible', 'destacado', 'creado')
    list_filter = ('disponible', 'destacado', 'categoria', 'marca', 'genero')
    search_fields = ('nombre', 'descripcion')
    prepopulated_fields = {"slug": ("nombre",)}
    inlines = (ProductSizeInline, ProductImageInline)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    prepopulated_fields = {"slug": ("nombre",)}


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    prepopulated_fields = {"slug": ("nombre",)}