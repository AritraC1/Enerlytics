from django.urls import path
from . import views

app_name = "dashboard"
urlpatterns = [
    path("", views.index, name="index"),
    # Health probe: registered with and without the trailing slash so pingers
    # hitting /health don't pay an APPEND_SLASH redirect.
    path("health", views.health, name="health"),
    path("health/", views.health),
    # HTMX partial refresh endpoint (filter panel): returns the
    # #dashboard-content fragment instead of the full page.
    path("partials/filtered/", views.filtered_partial, name="filtered"),
    # ML features: PESTLE prediction form and model quality report.
    path("predict/", views.predict, name="predict"),
    path("model-metrics/", views.model_metrics, name="model-metrics"),
]