from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render

from .services import get_dashboard_context


def index(request):
    """Full dashboard page: filters + KPI cards + charts + insights table.

    GET params are validated by DashboardFilterForm (see dashboard.services)
    and applied to the shared queryset, so one filter controls every chart.
    """
    return render(request, "dashboard/index.html", get_dashboard_context(request.GET))


def filtered_partial(request):
    """HTMX endpoint behind the filter panel (dashboard:filtered).

    Returns only the #dashboard-content fragment (filters + KPIs + charts +
    table) so htmx can swap it in without a page reload; hx-push-url keeps
    the active filters in the browser URL.
    """
    return render(
        request,
        "dashboard/partials/dashboard_content.html",
        get_dashboard_context(request.GET),
    )


def health(request):
    """Liveness/readiness probe (GET /health): app up + database reachable."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        return JsonResponse({"status": "error", "database": "unreachable"}, status=503)
    return JsonResponse({"status": "ok", "database": "ok"})
