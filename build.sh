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
