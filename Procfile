release: python manage.py migrate && python manage.py collectstatic --noinput
web: gunicorn studypulse_project.wsgi:application --bind 0.0.0.0:$PORT

