from django.core.management.base import BaseCommand
from client.models import Cliente
from seeder_flag.models import SeederStatus
from django.contrib.auth.models import User
from faker import Faker
import random

class Command(BaseCommand):
    help = 'Seed the database with sample clients'

    def add_arguments(self, parser):
        parser.add_argument('--number', type=int, default=15, help='Number of clients to create')

    def handle(self, *args, **options):
        status, created = SeederStatus.objects.get_or_create(name='seed_clients')

        if status.executed:
            self.stdout.write(self.style.WARNING('Clients already seeded.'))
            return

        fake = Faker('es_ES')  # Español de España
        number = options['number']
        
        self.stdout.write(self.style.WARNING(f'Creating {number + 1} clients...'))

        user, created = User.objects.get_or_create(
            username='cliente1',
            defaults={
                'email': 'cliente1@example.com'
            }
        )
        if created:
            user.set_password('password123')
            user.save()

            Cliente.objects.get_or_create(
                user=user,
                defaults={
                    'telefono': fake.phone_number()[:15],
                    'direccion': fake.address()[:50],
                    'ciudad': fake.city()[:50],
                    'codigo_postal': fake.postcode()[:50]
                }
            )
        
        for i in range(number):
            # Crear usuario
            username = fake.user_name()
            email = fake.email()

            if User.objects.filter(username=username).exists():
                continue

            user = User.objects.create_user(
                username=username,
                email=email,
                password='password123'
            )

            Cliente.objects.create(
                user=user,
                telefono=fake.phone_number()[:15],
                direccion=fake.address()[:50],
                ciudad=fake.city()[:50],
                codigo_postal=fake.postcode()[:50]
            )

        status.executed = True
        status.save()
        
        self.stdout.write(self.style.SUCCESS(f'Successfully created {number + 1} clients!'))