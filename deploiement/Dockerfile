# Image de l'interface web. La base reste le conteneur de docker-compose.yml.
#   docker build -f deploiement/Dockerfile -t veille-web .
#   docker run --env-file .env -p 127.0.0.1:8001:8001 veille-web
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN DEBUG=false SECRET_KEY=construction python manage.py collectstatic --noinput
ENV DEBUG=false VEILLE_WEB_BIND=0.0.0.0:8001 PYTHONUNBUFFERED=1
EXPOSE 8001
CMD ["gunicorn", "--config", "deploiement/gunicorn.conf.py", "Offre.wsgi:application"]
