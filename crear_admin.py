import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

admin_username = os.getenv('ADMIN_USERNAME', 'admin')
admin_email = os.getenv('ADMIN_EMAIL', 'admin@taller.com')
admin_password = os.getenv('ADMIN_PASSWORD', 'Taller2026!')

if not User.objects.filter(username=admin_username).exists():
    User.objects.create_superuser(admin_username, admin_email, admin_password)
    print(f">>> Superusuario '{admin_username}' creado exitosamente.")
else:
    print(f">>> El superusuario '{admin_username}' ya existe.")