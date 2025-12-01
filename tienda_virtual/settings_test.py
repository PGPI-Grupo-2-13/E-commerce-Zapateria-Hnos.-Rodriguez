from .settings import *

# Ajustes para ejecutar pruebas localmente usando SQLite (archivo en el repo)
# Este archivo se puede pasar con --settings para ejecutar tests sin tocar settings.py

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(BASE_DIR / 'test_db.sqlite3'),  # archivo sqlite para tests
    }
}
