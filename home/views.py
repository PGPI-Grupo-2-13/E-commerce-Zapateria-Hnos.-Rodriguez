from unittest import loader
from django.shortcuts import render
from .models import Escaparate, Articulo

def index(request):
    escaparates = Escaparate.objects.all()
    escaparate = escaparates.first()
    articulos = Articulo.objects.filter(pk = escaparate.articulo.id)
    articulo = articulos.first()
    contexto = {
        'nombre_articulo': articulo.nombre,
    }