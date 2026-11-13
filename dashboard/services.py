"""
Glue between the dashboard's validated filters and insights.services.

insights.services owns every calculation; this module only:
1. validates the incoming GET params with DashboardFilterForm,
2. turns the cleaned values into the params dict that
   insights.services.filtered_insights() applies to the queryset,
3. assembles the shared context (form + KPIs + charts + recent-records
   table) used by both the full page and the HTMX partial.

Because every KPI and chart is computed from one pre-filtered queryset, a
single filter selection controls the whole dashboard.
"""

from insights.services import filtered_insights, get_dashboard_data

from .forms import DashboardFilterForm

# Rows shown in the "Recent Insights" table (newest first).
TABLE_ROWS = 25
# Fields the table template touches; .only() keeps the query lean.
TABLE_FIELDS = (
    "title",
    "sector",
    "region",
    "pestle",
    "intensity",
    "likelihood",
    "relevance",
    "published",
)


def get_dashboard_context(data=None):
    """Validate `data` (usually request.GET) and compute the dashboard context.

    Invalid values are reported on the form but never reach the queryset —
    only fields that pass ChoiceField validation are applied as filters.
    """
    form = DashboardFilterForm(data or None)
    form.is_valid()  # Populates cleaned_data / errors either way.
    # cleaned_data stays valid even when other fields failed, so apply
    # whatever validated; invalid values only surface as form errors.
    cleaned = getattr(form, "cleaned_data", None) or {}
    params = {key: value for key, value in cleaned.items() if value}

    # One filtered queryset feeds every KPI, chart and the table.
    base = filtered_insights(params=params)
    stats = get_dashboard_data(qs=base)
    records = list(base.only(*TABLE_FIELDS)[:TABLE_ROWS])

    return {
        "form": form,
        "kpis": stats["kpis"],
        "charts": stats["charts"],
        "records": records,
        "shown": len(records),
        # "Total Insights" is the first KPI from get_kpis().
        "total": stats["kpis"][0]["value"],
        "has_filters": bool(params),
    }
