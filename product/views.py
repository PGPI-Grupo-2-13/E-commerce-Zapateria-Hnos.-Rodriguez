# Create your views here.

from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from .models import Product, Category, Brand


def product_list(request):
    """Lista de productos con filtros"""
    products = Product.objects.filter(disponible=True).select_related('categoria', 'marca').prefetch_related('imagenes')
    
    # Filtros
    categoria_slug = request.GET.get('categoria')
    marca_slug = request.GET.get('marca')
    genero = request.GET.get('genero')
    search = request.GET.get('search')
    
    if categoria_slug:
        products = products.filter(categoria__slug=categoria_slug)
    if marca_slug:
        products = products.filter(marca__slug=marca_slug)
    if genero:
        products = products.filter(genero=genero)
    if search:
        products = products.filter(nombre__icontains=search)
    
    # Paginación
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Datos para filtros
    categorias = Category.objects.all()
    marcas = Brand.objects.all()
    
    context = {
        'page_obj': page_obj,
        'categorias': categorias,
        'marcas': marcas,
        'categoria_actual': categoria_slug,
        'marca_actual': marca_slug,
        'genero_actual': genero,
        'search_query': search,
    }
    return render(request, 'product/product_list.html', context)


def product_detail(request, slug):
    """Detalle de producto"""
    product = get_object_or_404(
        Product.objects.prefetch_related('imagenes', 'tallas').select_related('categoria', 'marca'),
        slug=slug,
        disponible=True
    )
    
    # Productos relacionados (misma categoría)
    related_products = Product.objects.filter(
        categoria=product.categoria,
        disponible=True
    ).exclude(id=product.id)[:4]
    
    context = {
        'product': product,
        'related_products': related_products,
    }
    return render(request, 'product/product_detail.html', context)


def category_list(request):
    """Lista de categorías"""
    categorias = Category.objects.all()
    context = {'categorias': categorias}
    return render(request, 'product/category_list.html', context)


def brand_list(request):
    """Lista de marcas"""
    marcas = Brand.objects.all()
    context = {'marcas': marcas}
    return render(request, 'product/brand_list.html', context)


def home(request):
    """Página de inicio"""
    productos_destacados = Product.objects.filter(
        disponible=True,
        destacado=True
    ).select_related('categoria', 'marca').prefetch_related('imagenes')[:8]
    
    categorias = Category.objects.all()[:6]
    
    context = {
        'productos_destacados': productos_destacados,
        'categorias': categorias,
    }
    return render(request, 'product/home.html', context)