from .settings import *

# Ajustes para ejecutar pruebas localmente usando SQLite (archivo en el repo)
# Este archivo se puede pasar con --settings para ejecutar tests sin tocar settings.py
#Ejemplo: python manage.py test seeder_flag --settings=tienda_virtual.settings_test

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(BASE_DIR / 'test_db.sqlite3'),  # archivo sqlite para tests
    }
}
