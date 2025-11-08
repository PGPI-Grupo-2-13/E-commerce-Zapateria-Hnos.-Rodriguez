from django.db import models

# Create your models here.
    
class Cliente(models.Model):
    nombre = models.CharField(max_length=15)
    apellidos = models.CharField(max_length=30)
    email = models.EmailField(unique=True)
    telefono = models.CharField(max_length=15, blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    direccion = models.TextField(blank=True, null=True)
    ciudad = models.CharField(max_length=50, blank=True, null=True)
    codigo_postal = models.CharField(max_length=10, blank=True, null=True)
    password = models.CharField(max_length=128)


    def __str__(self):
        return f"{self.nombre} {self.apellidos}"
    
