from django.contrib import admin

from .models import Insight


@admin.register(Insight)
class InsightAdmin(admin.ModelAdmin):
    list_display = ("title", "sector", "topic", "region", "country", "intensity", "likelihood")
    list_filter = ("sector", "topic", "region", "pestle", "source")
    search_fields = ("title", "insight", "country", "source")
    date_hierarchy = "published"
