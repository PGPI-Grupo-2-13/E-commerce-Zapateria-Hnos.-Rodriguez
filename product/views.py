from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from .models import Product, Category, Brand
from pedido.models import Carrito
from client.models import Cliente


def _get_carrito_context(request):
    """Función auxiliar para obtener el carrito del usuario o sesión"""
    carrito = None
    if request.user.is_authenticated:
        try:
            cliente = Cliente.objects.get(user=request.user)
            carrito = Carrito.objects.filter(cliente=cliente).first()
        except Cliente.DoesNotExist:
            pass
    else:
        if request.session.session_key:
            carrito = Carrito.objects.filter(session_key=request.session.session_key).first()
    return {'carrito': carrito}


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
    
    # Añadir carrito al contexto
    context.update(_get_carrito_context(request))
    
    return render(request, 'product_list.html', context)


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
    ).exclude(id=product.id).prefetch_related('imagenes')[:4]
    
    context = {
        'product': product,
        'related_products': related_products,
    }
    
    # Añadir carrito al contexto
    context.update(_get_carrito_context(request))
    
    return render(request, 'product_detail.html', context)


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
    
    # Añadir carrito al contexto
    context.update(_get_carrito_context(request))
    
    return render(request, 'home.html', context)