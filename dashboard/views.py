import json
from datetime import datetime

from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render

from ml.predict import predict_pestle
from ml.training import METRICS_PATH

from .forms import PredictTitleForm
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


def predict(request):
    """Predict page (dashboard:predict).

    GET renders the form. POST validates the title, calls ml.predict, and
    returns either the full page (no-JS fallback) or — for HTMX requests —
    only the #prediction-result fragment, which hx-target swaps into place
    without a reload.
    """
    form = PredictTitleForm(request.POST if request.method == "POST" else None)
    result = None

    if request.method == "POST" and form.is_valid():
        result = predict_pestle(form.cleaned_data["title"])
        context = {"form": form, "result": result, "input_title": form.cleaned_data["title"]}
        if request.headers.get("HX-Request") == "true":
            return render(request, "dashboard/partials/prediction_result.html", context)

    return render(
        request,
        "dashboard/predict.html",
        {"form": form, "result": result},
    )


def _per_class_rows(report):
    """Per-class metric rows for the metrics table, in labels.json order.

    classification_report's output_dict mixes summary rows ("accuracy",
    "macro avg", "weighted avg") in with the classes; those are skipped.
    """
    return [
        {
            "label": label,
            "precision": values["precision"],
            "recall": values["recall"],
            "f1": values["f1-score"],
            "support": int(values["support"]),
        }
        for label, values in report.items()
        if label not in ("accuracy", "macro avg", "weighted avg")
    ]


def model_metrics(request):
    """Model metrics page (dashboard:model-metrics).

    Reads the committed ml/artifacts/metrics.json written by
    ``manage.py train_model`` and renders baseline-vs-model scores, the
    per-class table, and the confusion matrix. A missing file is a friendly
    "not trained yet" message, not a 500.
    """
    try:
        metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        metrics = None

    context = {"metrics": metrics}
    if metrics:
        labels = metrics.get("classes", [])
        matrix = metrics.get("confusion_matrix", [])
        try:
            trained_at = datetime.fromisoformat(metrics["trained_at"])
        except (KeyError, ValueError):
            trained_at = None
        context.update(
            {
                "per_class": _per_class_rows(metrics.get("per_class_report", {})),
                "matrix": list(zip(labels, matrix)),
                "labels": labels,
                "trained_at": trained_at,
                "top_confusion": sorted(
                    (
                        {
                            "true": labels[r],
                            "predicted": labels[c],
                            "count": int(count),
                        }
                        for r, row in enumerate(matrix)
                        for c, count in enumerate(row)
                        if count and r != c
                    ),
                    key=lambda row: row["count"],
                    reverse=True,
                )[:5],
            }
        )

    return render(request, "dashboard/model_metrics.html", context)


def health(request):
    """Liveness/readiness probe (GET /health): app up + database reachable."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        return JsonResponse({"status": "error", "database": "unreachable"}, status=503)
    return JsonResponse({"status": "ok", "database": "ok"})
