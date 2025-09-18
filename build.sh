#!/usr/bin/env bash

# Upgrade pip and install requirements
echo "📦 Installing dependencies..."
python -m pip install --upgrade pip
pip install -r requirements.txt

# Collect static files
echo "📚 Collecting static files..."
python manage.py collectstatic --no-input --clear

# Apply database migrations
echo "🔄 Running migrations..."
python manage.py migrate