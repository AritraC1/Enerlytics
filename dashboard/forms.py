"""
Filter panel form for the Enerlytics dashboard.

One ChoiceField per dashboard filter (sector / region / PESTLE). Choices are
built from the values actually present in the database, so the dropdowns can
never drift from the data, and ChoiceField validation guarantees only known
values reach insights.services.filtered_insights().

An empty value ("" — the "All ..." option) means "no filter" for that
dimension; filtered_insights() ignores empty params.
"""

from django import forms

from insights.models import Insight

EMPTY_LABELS = {
    "sector": "All sectors",
    "region": "All regions",
    "pestle": "All PESTLE axes",
}


def _distinct_choices(field):
    """(value, value) pairs for every non-empty value of `field`.

    Values are deduped case-insensitively and sorted for the dropdown.
    """
    values = set(
        Insight.objects.exclude(**{field: ""}).values_list(field, flat=True)
    )
    canonical = {}
    for value in sorted(values, key=str.casefold):
        canonical.setdefault(value.lower(), value)
    if field == "region" and "world" in canonical:
        # One canonical option; the iexact lookup matches "world" too.
        canonical["world"] = "World"
    return [(value, value) for value in sorted(canonical.values(), key=str.casefold)]


class DashboardFilterForm(forms.Form):
    """Sector / region / PESTLE filters for the dashboard."""

    sector = forms.ChoiceField(required=False, label="Sector")
    region = forms.ChoiceField(required=False, label="Region")
    pestle = forms.ChoiceField(required=False, label="PESTLE")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in self.fields:
            self.fields[name].choices = [
                ("", EMPTY_LABELS[name])
            ] + _distinct_choices(name)
            self.fields[name].widget.attrs.update(
                {"class": "filter-select", "aria-label": self.fields[name].label}
            )
