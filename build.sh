#!/usr/bin/env bash
# exit on error
set -o errexit

# Set environment variable to indicate we're on Render
export RENDER=True

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Apply migrations
python manage.py migrate

# Create default site if it doesn't exist
python manage.py shell -c "
from django.contrib.sites.models import Site
Site.objects.get_or_create(id=1, defaults={'domain': 'hosting-kq0v.onrender.com', 'name': 'LogU Travel Agency'})
"
