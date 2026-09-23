import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DjangoProject.settings')
application = get_wsgi_application()

# Only the served app warms up; manage.py commands never import this module.
from Bird_Sound.warmup import start_model_warmup  # noqa: E402

start_model_warmup()
