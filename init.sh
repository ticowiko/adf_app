#!/bin/bash

set -o pipefail

export PYSPARK_PYTHON=`which python3`
rm -f db.sqlite3
rm -f adf_web_ui/migrations/0*_*.py
rm -rf media
pip install -r requirements.txt
python -c "import secrets; print(secrets.token_urlsafe())" > secret_key.txt
export DJANGO_SECRET_KEY=`cat secret_key.txt`
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --no-input
export DJANGO_SUPERUSER_PASSWORD=admin
python manage.py createsuperuser --no-input --username admin --email youremail@yourdomain.com
