from django.core.management.base import BaseCommand
from accounts.models import User

class Command(BaseCommand):
    help = 'Seed initial users: CEO and SuperAdmin'

    def handle(self, *args, **options):
        # 1. SuperAdmin
        superadmin_email = 'iamsuperadmin@gmail.com'
        superadmin_pwd = 'HelloeAdmin1234!'
        
        if not User.objects.filter(email=superadmin_email).exists():
            User.objects.create_superuser(
                email=superadmin_email,
                nama='Super Admin',
                nomor_telepon='08123456789',
                password=superadmin_pwd,
            )
            self.stdout.write(self.style.SUCCESS(f'SuperAdmin created: {superadmin_email}'))
        else:
            self.stdout.write(self.style.WARNING(f'SuperAdmin {superadmin_email} already exists.'))

        # 2. CEO (who is also Komisaris)
        ceo_email = 'aruanregina@gmail.com'
        ceo_pwd = 'CEO1234!'
        
        if not User.objects.filter(email=ceo_email).exists():
            User.objects.create_user(
                email=ceo_email,
                nama='Regina Aruan',
                nomor_telepon='08987654321',
                password=ceo_pwd,
                role='CEO',
            )
            self.stdout.write(self.style.SUCCESS(f'CEO created: {ceo_email}'))
        else:
            # Update role to CEO if needed? 
            # The constraint is CEO dan Komisaris itu 1 orang.
            # Usually we pick one role for the field.
            self.stdout.write(self.style.WARNING(f'CEO {ceo_email} already exists.'))
