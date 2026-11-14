"""
Filter panel form for the Enerlytics dashboard, plus the Predict form.

One ChoiceField per dashboard filter (sector / region / PESTLE). Choices are
built from the values actually present in the database, so the dropdowns can
never drift from the data, and ChoiceField validation guarantees only known
values reach insights.services.filtered_insights().

An empty value ("" — the "All ..." option) means "no filter" for that
dimension; filtered_insights() ignores empty params.
"""

from django import forms

from insights.models import Insight
from ml.predict import MIN_TEXT_CHARS

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


class PredictTitleForm(forms.Form):
    """One text field: the insight title the PESTLE model predicts for.

    The same minimum length as ml.predict.MIN_TEXT_CHARS (imported, so the
    form and the model can never drift apart): shorter titles carry no
    usable TF-IDF signal. The maximum keeps absurdly long input out of the
    vectorizer; real titles in the dataset are far shorter.
    """

    MIN_CHARS = MIN_TEXT_CHARS
    MAX_CHARS = 200

    title = forms.CharField(
        label="Insight title",
        min_length=MIN_TEXT_CHARS,
        max_length=MAX_CHARS,
        strip=True,
        error_messages={
            "min_length": (
                "Please give at least %(limit_value)d characters of the title."
            ),
            "max_length": (
                "Please keep the title under %(limit_value)d characters."
            ),
            "required": "Type an insight title to predict.",
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["title"].widget.attrs.update(
            {
                "class": "predict-input",
                "placeholder": "e.g. Solar costs fall across oil and gas markets",
                "aria-label": "Insight title",
                "autocomplete": "off",
                "maxlength": str(self.MAX_CHARS),
            }
        )


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
