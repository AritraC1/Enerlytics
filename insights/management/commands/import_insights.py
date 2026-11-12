import json
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from insights.models import Insight

# Matches values like "January, 20 2017 03:51:25" in data/jsondata.json.
DATE_FORMAT = "%B, %d %Y %H:%M:%S"

# Sane projection-horizon bounds for start_year/end_year. Forecast years up to
# ~2100 are legitimate in this dataset; anything beyond (e.g. 2126, 2200) is a
# data-entry error and is dropped to NULL.
YEAR_MIN, YEAR_MAX = 2000, 2100


class Cleaner:
    """Normalizes one JSON record and tallies the fixes applied."""

    def __init__(self):
        self.trimmed = 0
        self.blank_numbers = 0
        self.blank_dates = 0
        self.bad_years = 0
        self.bad_dates = 0

    def text(self, value):
        if not isinstance(value, str):
            return "" if value in (None, "") else str(value)
        stripped = value.strip()
        if stripped != value:
            self.trimmed += 1
        return stripped

    def number(self, value):
        # The JSON uses "" for missing numbers.
        if value in ("", None):
            self.blank_numbers += 1
            return None
        return int(value)

    def year(self, value):
        if value in ("", None):
            self.blank_numbers += 1
            return None
        year = int(value)
        if not YEAR_MIN <= year <= YEAR_MAX:
            self.bad_years += 1
            return None
        return year

    def date(self, value):
        if not isinstance(value, str) or not value.strip():
            self.blank_dates += 1
            return None
        try:
            parsed = datetime.strptime(value.strip(), DATE_FORMAT)
        except ValueError:
            self.bad_dates += 1
            return None
        # The JSON carries no timezone info; treat values as project-local time.
        return timezone.make_aware(parsed)


def clean_record(record, cleaner):
    """Map one JSON object onto Insight field values, cleaning as we go."""
    return {
        "end_year": cleaner.year(record["end_year"]),
        "intensity": cleaner.number(record["intensity"]),
        "sector": cleaner.text(record["sector"]),
        "topic": cleaner.text(record["topic"]),
        "insight": cleaner.text(record["insight"]),
        "url": cleaner.text(record["url"]),
        "region": cleaner.text(record["region"]),
        "start_year": cleaner.year(record["start_year"]),
        "impact": cleaner.number(record["impact"]),
        "added": cleaner.date(record["added"]),
        "published": cleaner.date(record["published"]),
        "country": cleaner.text(record["country"]),
        "relevance": cleaner.number(record["relevance"]),
        "pestle": cleaner.text(record["pestle"]),
        "source": cleaner.text(record["source"]),
        "title": cleaner.text(record["title"]),
        "likelihood": cleaner.number(record["likelihood"]),
    }


class Command(BaseCommand):
    help = "Clean data/jsondata.json and (re)load it into the Insight table."

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            default=str(settings.BASE_DIR / "data" / "jsondata.json"),
            help="Path to the JSON source file.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Clean and report, but do not touch the database.",
        )

    def handle(self, *args, **options):
        path = Path(options["json"])
        if not path.is_file():
            raise CommandError(f"JSON file not found: {path}")

        records = json.loads(path.read_text(encoding="utf-8"))

        cleaner = Cleaner()
        seen = set()
        skipped = duplicated = 0
        rows = []
        for record in records:
            # A record is unusable without something to show or link to.
            if not str(record.get("title") or "").strip() or not str(record.get("url") or "").strip():
                skipped += 1
                continue
            key = (record.get("title"), record.get("url"), record.get("published"))
            if key in seen:
                duplicated += 1
                continue
            seen.add(key)
            rows.append(Insight(**clean_record(record, cleaner)))

        report = (
            f"Read {len(records)} records from {path}\n"
            f"Dropped {skipped} malformed record(s) and {duplicated} in-file duplicate(s)\n"
            f"Cleaned: {cleaner.trimmed} string(s) trimmed, "
            f"{cleaner.blank_numbers} blank number(s) -> NULL, "
            f"{cleaner.blank_dates} blank date(s) -> NULL, "
            f"{cleaner.bad_dates} unparseable date(s) -> NULL, "
            f"{cleaner.bad_years} out-of-range year(s) -> NULL"
        )
        self.stdout.write(report)

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("Dry run: nothing written."))
            return

        with transaction.atomic():
            # Idempotent by design: one command always yields exactly this
            # dataset, no matter how many times it runs.
            deleted, _ = Insight.objects.all().delete()
            Insight.objects.bulk_create(rows, batch_size=500)

        self.stdout.write(
            self.style.SUCCESS(
                f"Replaced {deleted} existing row(s); loaded {len(rows)} clean insights."
            )
        )
