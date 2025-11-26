from django.shortcuts import render
from product.models import Product

def home(request):
    productos_destacados = Product.objects.filter(disponible=True).order_by('?')[:3]
    return render(request, 'home.html', {'productos_destacados': productos_destacados})