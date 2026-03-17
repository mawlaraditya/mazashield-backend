import os
import django
from django.db import connection
from django.utils import timezone
from django.apps import apps

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MazaShield.settings')
django.setup()

def fix_all():
    # Daftar app yang mau dipaksa record migrasinya
    apps_to_fake = ['accounts', 'catalogs', 'contenttypes', 'auth', 'admin', 'sessions']
    
    with connection.cursor() as cursor:
        for app_label in apps_to_fake:
            # Kita asumsikan semua pakai 0001_initial untuk tahap awal ini
            migration_name = '0001_initial'
            
            cursor.execute(
                "SELECT id FROM django_migrations WHERE app=%s AND name=%s",
                [app_label, migration_name]
            )
            
            if not cursor.fetchone():
                print(f"Injecting {app_label}.{migration_name}...")
                cursor.execute(
                    "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, %s)",
                    [app_label, migration_name, timezone.now()]
                )
        
        print("All base migrations have been recorded in django_migrations.")

if __name__ == "__main__":
    fix_all()
