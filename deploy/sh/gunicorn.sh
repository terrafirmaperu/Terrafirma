#!/bin/bash

NAME="factora"
DJANGODIR=$(dirname $(dirname $(cd `dirname $0` && pwd)))
SOCKFILE=/tmp/gunicorn.sock
LOGDIR=${DJANGODIR}/logs/gunicorn.log
USER=jair
GROUP=jair
NUM_WORKERS=5
DJANGO_SETTINGS_MODULE=config.production
DJANGO_WSGI_MODULE=config.wsgi
TIMEOUT=600000

rm -frv $SOCKFILE

echo $DJANGODIR
cd $DJANGODIR
echo "Iniciando la aplicación $NAME con el usuario `whoami`"

exec ${DJANGODIR}/env/bin/gunicorn ${DJANGO_WSGI_MODULE}:application \
  --name $NAME \
  --workers $NUM_WORKERS \
  --timeout $TIMEOUT \
  --user=$USER --group=$GROUP \
  --bind=unix:$SOCKFILE \
  --log-level=debug \
  --log-file=$LOGDIR