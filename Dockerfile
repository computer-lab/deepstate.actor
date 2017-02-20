FROM ubuntu:xenial
MAINTAINER rob@computerlab.io
WORKDIR /opt/deepstate/

# Installs system deps
RUN apt-get update && apt-get install -y \
    libpq-dev \
    nginx \
    python3 \
    python3-pip

# Adds SSL certificates / keys
COPY ops/certs/${NGINX_SSL_CERTIFICATE} \
     /etc/ssl/certs/${NGINX_SSL_CERTIFICATE}
COPY ops/keys/${NGINX_SSL_CERTIFICATE_KEY} \
     /etc/ssl/private/${NGINX_SSL_CERTIFICATE_KEY}

# Sets up nginx
COPY ops/config/deepstate-nginx /etc/nginx/sites-available/deepstate
RUN rm /etc/nginx/sites-enabled/*
RUN ln -s \
    /etc/nginx/sites-available/deepstate \
    /etc/nginx/sites-enabled/deepstate

# Installs application deps
RUN pip3 install -U pip
RUN pip3 install gunicorn
COPY app/requirements.txt .
RUN pip3 install -r requirements.txt
COPY app/ .

# Runs the application
CMD service nginx start \
    && until (python3 manage.py migrate); do sleep 1; done \
    && gunicorn --access-logfile=- --error-logfile=- --max-requests=10 -w 8 deepstate.wsgi
