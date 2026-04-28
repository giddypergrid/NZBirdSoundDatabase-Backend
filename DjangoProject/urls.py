from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('birds/', include('Bird_Sound.urls')),
    # Prometheus-format metrics for Grafana/Prometheus scrapers.
    # In prod, restrict access to this URL via nginx (allow only localhost
    # and your monitoring agent's IP).
    path('', include('django_prometheus.urls')),
]
