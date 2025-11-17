"""
URL configuration for tienda_virtual project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from home import views as homeViews
from pedido import views as pedidoViews

urlpatterns = [
    path('', homeViews.home, name="home"),
    path('admin/', admin.site.urls),
    path('productos/', include('product.urls', namespace='product')),
    path('clientes/', include('client.urls')),
    
    path('carrito/', pedidoViews.carrito_compra, name='carrito_compra'),  # ← La mantuve
    path('carrito/agregar/<int:producto_id>/', pedidoViews.agregar_al_carrito, name='agregar_al_carrito'),  # ← Nueva
    path('carrito/actualizar/<int:item_id>/', pedidoViews.actualizar_cantidad_carrito, name='actualizar_cantidad_carrito'),  # ← Nueva
    path('carrito/eliminar/<int:item_id>/', pedidoViews.eliminar_del_carrito, name='eliminar_del_carrito'),  # ← Nueva
    path('carrito/vaciar/', pedidoViews.vaciar_carrito, name='vaciar_carrito'),  # ← Nueva
    
    path('pedidos/', pedidoViews.listado_pedidos, name='pedidos'),
    path('pedidos/<int:pedido_id>/', pedidoViews.detalle_pedido, name='detalle_pedido'),
]
