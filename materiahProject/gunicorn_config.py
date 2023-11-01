wsgi_app = "materiahProject.wsgi:application"
bind = "0.0.0.0:8000"
reload = True
workers = 3
pidfile = "/var/www/materiahProject/runtime/gunicorn.pid"
errorlog = '/var/www/materiahProject/logs/gunicorn-error.log'
accesslog = '/var/www/materiahProject/logs/gunicorn-access.log'
