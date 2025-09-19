release: python manage.py migrate && python manage.py collectstatic --noinput
web: gunicorn studypulse_project.wsgi --log-file -
