from django.urls import path
from . import views

urlpatterns = [
    path(
        "checkout/<str:numero_pedido>/",
        views.checkout_pedido,
        name="checkout_pedido"
    ),
    path(
        "checkout/<str:numero_pedido>/exito/",
        views.pedido_pago_exito,
        name="pedido_pago_exito"
    ),
    path(
        "checkout/<str:numero_pedido>/error/",
        views.pedido_pago_error,
        name="pedido_pago_error"
    ),

    path(
        "mis-pedidos/",
        views.listado_pedidos,
        name="listado_pedidos"
    ),
    path(
        "detalle/<int:pedido_id>/",
        views.detalle_pedido,
        name="detalle_pedido"
    ),
    path(
        "crear-pedido/",
        views.crear_pedido_desde_carrito,
        name="crear_pedido"
    ),
    path(
        "checkout/<str:numero_pedido>/",
        views.checkout_pedido,
        name="checkout_pedido"
    ),
    path(
        "checkout/<str:numero_pedido>/exito/",
        views.pedido_pago_exito,
        name="pedido_pago_exito"
    ),
    path(
        "checkout/<str:numero_pedido>/error/",
        views.pedido_pago_error,
        name="pedido_pago_error"
    ),
]