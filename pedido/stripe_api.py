from decimal import Decimal
import stripe
from django.conf import settings
import stripe.error

stripe.api_key = settings.STRIPE_SECRET_KEY


def calcular_total_cents(pedido) -> int:
    """
    Calcula el total del pedido en céntimos para Stripe.
    total = subtotal + impuestos + coste_entrega - descuento
    """
    total = (
        pedido.subtotal
        + pedido.impuestos
        + pedido.coste_entrega
        - pedido.descuento
    )
    total = Decimal(total)
    return int(total * Decimal("100"))


def create_payment_intent(pedido):
    """
    Crea un PaymentIntent en Stripe para el pedido dado.
    Devuelve el objeto PaymentIntent o None si hay error.
    """
    try:
        amount_cents = calcular_total_cents(pedido)

        payment_intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency="eur",
            automatic_payment_methods={"enabled": True},
            metadata={
                "pedido_id": pedido.id,
                "numero_pedido": pedido.numero_pedido,
                "cliente_id": pedido.cliente_id,
            },
        )

        return payment_intent

    except stripe.error.StripeError as e:
        print(f"[Stripe] Error: {getattr(e, 'user_message', str(e))}")
        return None
