from django.db import models

class SeederStatus(models.Model):
    name = models.CharField(max_length=100, unique=True)
    executed = models.BooleanField(default=False)
    executed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Seeder Statuses"

    def __str__(self):
        return f"{self.name} - {'Executed' if self.executed else 'Pending'}"