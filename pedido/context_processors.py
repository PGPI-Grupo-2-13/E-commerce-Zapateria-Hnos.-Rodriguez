from .views import _get_or_create_carrito

def carrito_context(request):
    """Añade el objeto Carrito al contexto de todas las plantillas."""
    
    carrito = _get_or_create_carrito(request)
    
    return {
        'carrito': carrito
    }