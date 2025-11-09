from django.db import models

# Create your models here.
class Articulo(models.Model):
    nombre = models.CharField(max_length=30)
    descripcion = models.CharField(max_length=100)
    
    def __str__(self):
        return self.nombre
    
class Escaparate(models.Model):
    articulo = models.ForeignKey(Articulo, on_delete=models.CASCADE)
    
    def __str__(self):
        return str(self.articulo.id)