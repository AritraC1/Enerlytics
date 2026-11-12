from django.shortcuts import render
from insights.models import Insight

# Create your views here.
def index(request):
    return render(request, "dashboard/index.html", {"total": Insight.objects.count()})