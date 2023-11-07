wsgi_app = "materiahProject.wsgi:application"
bind = "127.0.0.1:8000"
reload = True
workers = 3
pidfile = "/var/www/materiah/materiahProject/runtime/gunicorn.pid"
errorlog = '/var/www/materiah/materiahProject/logs/gunicorn-error.log'
accesslog = '/var/www/materiah/materiahProject/logs/gunicorn-access.log'
