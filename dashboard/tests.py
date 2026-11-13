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
