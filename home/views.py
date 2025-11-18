from django.shortcuts import render
from product.models import Product

def home(request):
    productos = Product.objects.all()

    return render(request, 'home.html', {
        'productos': productos,
    })
