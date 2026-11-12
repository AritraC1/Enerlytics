from django.db import models


class Insight(models.Model):
    """
    One curated energy / sustainability insight record.

    Field names and order mirror data/jsondata.json so the JSON can be
    loaded directly. Numeric fields are nullable because the JSON uses ""
    (empty string) where a value is missing; `added`/`published` are parsed
    from "%B, %d %Y %H:%M:%S" strings at import time.
    """

    end_year = models.IntegerField(null=True, blank=True)
    intensity = models.IntegerField(null=True, blank=True)
    sector = models.CharField(max_length=64, blank=True, default="")
    topic = models.CharField(max_length=64, blank=True, default="")
    insight = models.TextField(blank=True)
    url = models.URLField(max_length=512, blank=True)
    region = models.CharField(max_length=64, blank=True, default="")
    start_year = models.IntegerField(null=True, blank=True)
    impact = models.IntegerField(null=True, blank=True)
    added = models.DateTimeField(null=True, blank=True)
    published = models.DateTimeField(null=True, blank=True)
    country = models.CharField(max_length=128, blank=True, default="")
    relevance = models.IntegerField(null=True, blank=True)
    pestle = models.CharField(max_length=64, blank=True, default="")
    source = models.CharField(max_length=128, blank=True, default="")
    title = models.TextField(blank=True)
    likelihood = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-published", "-added"]

    def __str__(self):
        return self.title
