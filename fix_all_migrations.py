import os
import django
from django.db import connection
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MazaShield.settings')
django.setup()

def fix_production():
    # Data lengkap hasil pemetaan dari branch development
    migrations_to_inject = [
        ('contenttypes', '0001_initial'),
        ('auth', '0001_initial'),
        ('admin', '0001_initial'),
        ('admin', '0002_logentry_remove_auto_add'),
        ('admin', '0003_logentry_add_action_flag_choices'),
        ('contenttypes', '0002_remove_content_type_name'),
        ('auth', '0002_alter_permission_name_max_length'),
        ('auth', '0003_alter_user_email_max_length'),
        ('auth', '0004_alter_user_username_opts'),
        ('auth', '0005_alter_user_last_login_null'),
        ('auth', '0006_require_contenttypes_0002'),
        ('auth', '0007_alter_validators_add_error_messages'),
        ('auth', '0008_alter_user_username_max_length'),
        ('auth', '0009_alter_user_last_name_max_length'),
        ('auth', '0010_alter_group_name_max_length'),
        ('auth', '0011_update_proxy_permissions'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('sessions', '0001_initial'),
        ('accounts', '0001_initial'),
        ('accounts', '0002_resetpasswordotp'),
        ('accounts', '0003_alter_resetpasswordotp_otp'),
        ('catalogs', '0001_initial'),
        ('catalogs', '0002_remove_ternak_umur_ternak_berat_target_ternak_jenis_and_more'),
        ('catalogs', '0003_daging'),
        ('catalogs', '0004_invest'),
        ('catalogs', '0005_invest_jenis'),
        ('catalogs', '0006_rename_harga_beli_invest_harga_sapi_and_more'),
    ]
    
    with connection.cursor() as cursor:
        print("Starting production migration repair...")
        for app, name in migrations_to_inject:
            cursor.execute(
                "SELECT id FROM django_migrations WHERE app=%s AND name=%s",
                [app, name]
            )
            if not cursor.fetchone():
                print(f"Injecting: {app}.{name}")
                cursor.execute(
                    "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, %s)",
                    [app, name, timezone.now()]
                )
            else:
                print(f"Skipping (already exists): {app}.{name}")
        
        print("Success! All migration records have been injected safely.")

if __name__ == "__main__":
    fix_production()
