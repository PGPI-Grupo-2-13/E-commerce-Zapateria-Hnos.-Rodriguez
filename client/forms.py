from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _


class SpanishAuthenticationForm(AuthenticationForm):
    error_messages = {
        'invalid_login': _(
            'Por favor, introduce un nombre de usuario y contraseña correctos. '
            'Ten en cuenta que ambos campos pueden ser sensibles a mayúsculas.'
        ),
        'inactive': _('Esta cuenta está inactiva.'),
    }
