from django.core.management.base import BaseCommand
from client.models import Cliente
from seeder_flag.models import SeederStatus
from django.contrib.auth.models import User
from faker import Faker

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

        # --- CLIENTE 1 (Usuario fijo) ---
        user, user_created = User.objects.get_or_create(
            username='cliente1',
            defaults={
                'email': 'cliente1@example.com'
            }
        )
        
        # Si el usuario se acaba de crear, la señal ya creó un Cliente vacío.
        # Si el usuario ya existía, obtenemos su cliente.
        if user_created:
            user.set_password('password123')
            user.save()

        # Actualizamos los datos del cliente existente (creado por la señal o previo)
        cliente, _ = Cliente.objects.get_or_create(user=user)
        cliente.telefono = fake.phone_number()[:15]
        cliente.direccion = fake.address()[:50]
        cliente.ciudad = fake.city()[:50]
        cliente.codigo_postal = fake.postcode()[:50]
        cliente.save()
        
        # --- RESTO DE CLIENTES (Bucle) ---
        for i in range(number):
            username = fake.user_name()
            email = fake.email()

            if User.objects.filter(username=username).exists():
                continue

            # Al crear el user, la señal en models.py CREA automáticamente el Cliente
            user = User.objects.create_user(
                username=username,
                email=email,
                password='password123'
            )

            # En vez de crear, obtenemos el cliente que la señal acaba de generar
            cliente = Cliente.objects.get(user=user)
            
            # Y actualizamos sus campos
            cliente.telefono = fake.phone_number()[:15]
            cliente.direccion = fake.address()[:50]
            cliente.ciudad = fake.city()[:50]
            cliente.codigo_postal = fake.postcode()[:50]
            cliente.save()

        status.executed = True
        status.save()
        
        self.stdout.write(self.style.SUCCESS(f'Successfully created {number + 1} clients!'))