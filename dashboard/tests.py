import unittest.mock
from pathlib import Path

from django.test import Client, TestCase
from django.urls import reverse

from insights.models import Insight


class DashboardUITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Insight.objects.create(
            title="Clean Energy Transition Accelerates",
            sector="Energy",
            topic="gas",
            region="Northern America",
            pestle="Economic",
            intensity=8,
            likelihood=4,
            relevance=4,
            country="United States of America",
        )
        Insight.objects.create(
            title="Battery Storage Tech Breakthrough",
            sector="Manufacturing",
            topic="battery",
            region="World",
            pestle="Technological",
            intensity=6,
            likelihood=3,
            relevance=5,
            country="Germany",
        )

    def setUp(self):
        self.client = Client()

    def test_dashboard_index_renders_successfully(self):
        response = self.client.get(reverse("dashboard:index"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/index.html")
        self.assertTemplateUsed(response, "base.html")
        self.assertTemplateUsed(response, "dashboard/partials/dashboard_content.html")
        # Check UI components
        content = response.content.decode("utf-8")
        self.assertIn("app-sidebar", content)
        self.assertIn("sidebar-toggle-btn", content)
        self.assertIn("data-tooltip", content)
        self.assertIn("kpi-grid", content)
        self.assertIn("chart-grid", content)
        self.assertIn("insights-table", content)
        self.assertIn("Clean Energy Transition Accelerates", content)

    def test_dashboard_filtered_partial(self):
        response = self.client.get(
            reverse("dashboard:filtered"),
            {"sector": "Energy"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/partials/dashboard_content.html")
        content = response.content.decode("utf-8")
        self.assertIn("Clean Energy Transition Accelerates", content)

    def test_health_endpoint(self):
        response = self.client.get(reverse("dashboard:health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")


class PredictPageTests(TestCase):
    """The Predict page: form render, prediction result, HTMX fragment."""

    @staticmethod
    def _stub_result(**overrides):
        """A fixed ml.predict-shaped result, so view tests don't depend on the
        gitignored model artifact being present."""
        result = {
            "available": True,
            "label": "Economic",
            "probability": 0.72,
            "top": [
                {"label": "Economic", "probability": 0.72},
                {"label": "Political", "probability": 0.18},
                {"label": "Technological", "probability": 0.10},
            ],
            "error": None,
        }
        result.update(overrides)
        return result

    def test_get_renders_form(self):
        response = self.client.get(reverse("dashboard:predict"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/predict.html")
        self.assertContains(response, "<form")

    def test_post_returns_category_with_confidence(self):
        with unittest.mock.patch(
            "dashboard.views.predict_pestle",
            return_value=self._stub_result(),
        ):
            response = self.client.post(
                reverse("dashboard:predict"),
                {"title": "Oil prices surge as supply concerns mount"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/predict.html")
        # Category badge and the top-3 confidence rows are rendered.
        self.assertContains(response, "Predicted category")
        self.assertContains(response, "confidence-row")

    def test_post_too_short_title_shows_validation_error(self):
        response = self.client.post(reverse("dashboard:predict"), {"title": "ab"})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/predict.html")
        # Django's min_length validator message; no result card is shown.
        self.assertContains(response, "at least")

    def test_htmx_post_returns_only_the_result_fragment(self):
        with unittest.mock.patch(
            "dashboard.views.predict_pestle",
            return_value=self._stub_result(),
        ):
            response = self.client.post(
                reverse("dashboard:predict"),
                {"title": "Oil prices surge as supply concerns mount"},
                headers={"HX-Request": "true"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateNotUsed(response, "dashboard/predict.html")
        self.assertTemplateUsed(response, "dashboard/partials/prediction_result.html")


class ModelMetricsPageTests(TestCase):
    """The Model metrics page: baseline vs model scores side by side."""

    def test_renders_metrics_with_baseline_and_model_scores(self):
        response = self.client.get(reverse("dashboard:model-metrics"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/model_metrics.html")
        content = response.content.decode("utf-8")
        # Baseline and model are reported side by side (not accuracy alone).
        self.assertIn("Baseline", content)
        self.assertIn("macro", content.lower())
        # Per-class breakdown present.
        self.assertIn("Technological", content)

    def test_missing_metrics_file_degrades_gracefully(self):
        with unittest.mock.patch(
            "dashboard.views.METRICS_PATH",
            Path("does/not/exist/metrics.json"),
        ):
            response = self.client.get(reverse("dashboard:model-metrics"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No metrics file yet")
