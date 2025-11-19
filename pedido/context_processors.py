from .views import _get_or_create_carrito
import logging

logger = logging.getLogger(__name__)

def carrito_context(request):
    """Añade el objeto Carrito al contexto de todas las plantillas."""
    try:
        carrito = _get_or_create_carrito(request)
        return {'carrito': carrito}
    except Exception as e:
        logger.error(f"Error crítico cargando el carrito (DB caída?): {e}")
        return {'carrito': None}