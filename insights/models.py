from django.db import models

# Create your models here.
class Insight(models.Model):
    """
    One curated energy / sustainability insight record. 
    """

    title = models.TextField()
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title