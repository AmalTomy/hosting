#!/usr/bin/env bash
# exit on error
set -o errexit

# Set environment variable to indicate we're on Render
export RENDER=True

# Install dependencies from production-specific requirements file
pip install -r requirements-prod.txt

# Collect static files
python manage.py collectstatic --no-input

# Apply migrations - make sure to run with --no-input and force-run to ensure all migrations are applied
python manage.py migrate --no-input --force-run

# Create default site if it doesn't exist
python manage.py shell -c "
from django.contrib.sites.models import Site
Site.objects.get_or_create(id=1, defaults={'domain': 'hosting-kq0v.onrender.com', 'name': 'LogU Travel Agency'})
"

# Create a superuser if it doesn't exist
python manage.py shell -c "
from home.models import Users
if not Users.objects.filter(email='admin@logu.com').exists():
    Users.objects.create_superuser('admin', 'admin@logu.com', 'Admin@123', user_type='admin', status='active')
    print('Superuser created successfully')
else:
    print('Superuser already exists')
"
