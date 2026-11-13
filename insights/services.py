"""
Central calculation layer for the Enerlytics dashboard.

Every number the dashboard shows is computed here with the ORM and returned
as plain, JSON-serializable dicts/lists. The views, future HTMX partials and
the AI assistant all reuse these functions instead of re-implementing logic.

Conventions:
- Blank categories (sector/region/pestle/topic) are grouped as "Unspecified".
- "World" and "world" are treated as one region.
- `impact` is populated on only ~3% of records, so "high impact" is proxied
  by `intensity >= HIGH_INTENSITY_MIN`.
"""

from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncYear

from insights.models import Insight

UNSPECIFIED = "Unspecified"

# Records with intensity at or above this count as "high-intensity".
HIGH_INTENSITY_MIN = 7
# Top-N slices for the topic/region charts.
TOP_N_TOPICS = 10
TOP_N_REGIONS = 10
# Intensity histogram range; anything above is lumped into the "10+" bucket.
INTENSITY_BUCKET_MAX = 10

# Accepted filter params -> ORM lookups. Kept for the filter panel and the
# AI assistant; the current page does not expose filters yet.
FILTER_LOOKUPS = {
    "sector": "sector",
    "region": "region__iexact",  # iexact merges "World" and "world"
    "topic": "topic__iexact",
    "pestle": "pestle",
    "source": "source",
    "country": "country",
}


def filtered_insights(params=None, qs=None):
    """Return an Insight queryset filtered by dashboard params.

    `params` maps filter names to values; blank/missing values are ignored,
    so an unfiltered page simply passes the GET dict through. Every other
    function in this module accepts a base queryset, which makes filters
    automatically apply to all KPIs and charts.
    """
    if qs is None:
        qs = Insight.objects.all()
    params = params or {}
    for key, lookup in FILTER_LOOKUPS.items():
        value = (params.get(key) or "").strip()
        if value:
            qs = qs.filter(**{lookup: value})
    return qs


def _normalize(value, blank=UNSPECIFIED):
    """Normalize a category value for display."""
    value = (value or "").strip()
    if not value:
        return blank
    if value.lower() == "world":
        return "World"
    return value


def _round(value, digits=1):
    """None-safe rounding for Avg() results."""
    return None if value is None else round(value, digits)


def _chart(chart_id, title, chart_type, labels=None, values=None, **extra):
    """Build one JSON-serializable chart spec for the frontend."""
    spec = {"id": chart_id, "title": title, "type": chart_type}
    if labels is not None:
        spec["labels"] = labels
    if values is not None:
        spec["values"] = values
    spec.update(extra)
    return spec


def _grouped_counts(values):
    """Count normalized category values, sorted by count desc, then name."""
    counts = {}
    for value in values:
        label = _normalize(value)
        counts[label] = counts.get(label, 0) + 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def get_kpis(qs=None):
    """Return the KPI cards as a list of {"label", "value"} dicts."""
    qs = filtered_insights(qs=qs)
    agg = qs.aggregate(
        total=Count("id"),
        avg_intensity=Avg("intensity"),
        avg_likelihood=Avg("likelihood"),
        avg_relevance=Avg("relevance"),
        high_intensity=Count("id", filter=Q(intensity__gte=HIGH_INTENSITY_MIN)),
    )
    return [
        {"label": "Total Insights", "value": agg["total"]},
        {
            "label": "Sectors Covered",
            "value": qs.exclude(sector="").values_list("sector", flat=True).distinct().count(),
        },
        {
            "label": "Countries Covered",
            "value": qs.exclude(country="").values_list("country", flat=True).distinct().count(),
        },
        {"label": "Avg Intensity", "value": _round(agg["avg_intensity"])},
        {"label": "Avg Likelihood", "value": _round(agg["avg_likelihood"])},
        {"label": "Avg Relevance", "value": _round(agg["avg_relevance"])},
        {
            "label": f"High-Intensity Insights (≥{HIGH_INTENSITY_MIN})",
            "value": agg["high_intensity"],
        },
    ]


def _sector_chart(qs):
    rows = qs.values("sector").annotate(count=Count("id")).order_by("-count")
    labels = [_normalize(row["sector"]) for row in rows]
    values = [row["count"] for row in rows]
    return _chart("sector", "Insights by Sector", "bar", labels, values)


def _topic_chart(qs):
    rows = (
        qs.exclude(topic="")
        .values("topic")
        .annotate(count=Count("id"))
        .order_by("-count")[:TOP_N_TOPICS]
    )
    labels = [_normalize(row["topic"], blank="") for row in rows]
    values = [row["count"] for row in rows]
    return _chart(
        "topics", f"Top {TOP_N_TOPICS} Discussed Topics", "bar", labels, values,
        horizontal=True,
    )


def _region_chart(qs):
    # Grouped in Python so "World"/"world" merge into one bar.
    pairs = _grouped_counts(qs.values_list("region", flat=True))
    labels = [label for label, _ in pairs]
    values = [count for _, count in pairs]
    return _chart("regions", "Insights by Region", "bar", labels, values)


def _pestle_chart(qs):
    rows = qs.values("pestle").annotate(count=Count("id")).order_by("-count")
    labels = [_normalize(row["pestle"]) for row in rows]
    values = [row["count"] for row in rows]
    return _chart("pestle", "PESTLE Distribution", "doughnut", labels, values)


def _intensity_chart(qs):
    # Bucketed in Python: intensity 1..10, outlier values lumped into "10+".
    values_raw = list(
        qs.filter(intensity__isnull=False).values_list("intensity", flat=True)
    )
    labels = [str(i) for i in range(1, INTENSITY_BUCKET_MAX)] + [f"{INTENSITY_BUCKET_MAX}+"]
    counts = [0] * len(labels)
    for value in values_raw:
        index = min(value, INTENSITY_BUCKET_MAX) - 1
        counts[index] += 1
    return _chart(
        "intensity", "Intensity Distribution", "bar", labels, counts,
    )


def _risk_chart(qs):
    points = list(
        qs.filter(intensity__isnull=False, likelihood__isnull=False)
        .values_list("intensity", "likelihood")
    )
    return _chart(
        "risk", "Likelihood vs Intensity", "scatter",
        points=[{"x": x, "y": y} for x, y in points],
    )


def _published_chart(qs):
    rows = (
        qs.filter(published__isnull=False)
        .annotate(year=TruncYear("published"))
        .values("year")
        .annotate(count=Count("id"))
        .order_by("year")
    )
    labels = [row["year"].year for row in rows]
    values = [row["count"] for row in rows]
    return _chart("published", "Insights Published per Year", "line", labels, values)


def get_chart_data(qs=None):
    """Return the list of chart specs the frontend renders."""
    qs = filtered_insights(qs=qs)
    return [
        _sector_chart(qs),
        _topic_chart(qs),
        _region_chart(qs),
        _pestle_chart(qs),
        _intensity_chart(qs),
        _risk_chart(qs),
        _published_chart(qs),
    ]


def get_dashboard_data(params=None, qs=None):
    """One call for the whole dashboard: {"kpis": [...], "charts": [...]}."""
    base = filtered_insights(params=params, qs=qs)
    return {
        "kpis": get_kpis(qs=base),
        "charts": get_chart_data(qs=base),
    }
