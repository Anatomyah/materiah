# wsgi_app is a string representing the path to your WSGI application callable,
# in the pattern of "{module_name}:{callable_name}".
wsgi_app = "materiahProject.wsgi:application"

# bind contains the address that the server should listen on; 
# in this case, it's set to the loopback address (127.0.0.1), port 8000.
bind = "127.0.0.1:8000"

# If the 'reload' option is True, the server will restart itself whenever it detects a code change. 
# This is basically meant to be used during development to ensure that the latest version of the app code is always running.
reload = True

# 'workers' defines the number of system worker processes that will be created to handle requests.
# Typically this is set to a value of 2-4 x $(NUM_CORES), depending on your application's workload. 
workers = 3

# 'pidfile' is used to specify a filename to use for the pid file. 
# The pid file stores the process id of the gunicorn master process.
# This file is used to manage the server. It's often used to stop or restart the server.
pidfile = "/var/www/materiah/materiahProject/runtime/gunicorn.pid"

# 'errorlog' is used to specify the location of the error log file.
# The server writes errors associated with the server operation to this file.
errorlog = '/var/www/materiah/materiahProject/logs/gunicorn-error.log'

# 'accesslog' is used to specify the location of the access log file.
# The server writes a log detailing each request that came to the server, as well as server responses, to this file.
accesslog = '/var/www/materiah/materiahProject/logs/gunicorn-access.log'
