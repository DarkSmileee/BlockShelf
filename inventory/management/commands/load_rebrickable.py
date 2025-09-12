import csv, gzip
from django.core.management.base import BaseCommand
from inventory.models import RBColor, RBPart, RBElement

def _open(path):
    # supports .csv and .csv.gz
    return gzip.open(path, mode="rt", encoding="utf-8") if path.lower().endswith(".gz") else open(path, "r", encoding="utf-8", newline="")

class Command(BaseCommand):
    help = "Load Rebrickable CSV dumps into local tables (colors, parts, elements)."

    def add_arguments(self, parser):
        parser.add_argument("--colors", help="Path to colors.csv or colors.csv.gz")
        parser.add_argument("--parts", help="Path to parts.csv or parts.csv.gz")
        parser.add_argument("--elements", help="Path to elements.csv or elements.csv.gz")
        parser.add_argument("--batch", type=int, default=5000, help="bulk_create batch size")

    def handle(self, *args, **opts):
        batch = opts["batch"]

        if opts["colors"]:
            self.stdout.write(self.style.MIGRATE_HEADING("Loading colors…"))
            created = updated = 0
            with _open(opts["colors"]) as f:
                for row in csv.DictReader(f):
                    cid = int(row["id"])
                    defaults = {
                        "name": (row.get("name") or "").strip(),
                        "rgb": (row.get("rgb") or "").strip().lstrip("#"),
                        "is_trans": str(row.get("is_trans") or "").strip().lower() in ("t", "true", "1"),
                    }
                    _, was_created = RBColor.objects.update_or_create(id=cid, defaults=defaults)
                    created += 1 if was_created else 0
                    updated += 0 if was_created else 1
            self.stdout.write(self.style.SUCCESS(f"Colors: +{created}, updated {updated}"))

        if opts["parts"]:
            self.stdout.write(self.style.MIGRATE_HEADING("Loading parts…"))
            created = updated = 0
            with _open(opts["parts"]) as f:
                for row in csv.DictReader(f):
                    part_num = (row["part_num"] or "").strip()
                    defaults = {
                        "name": (row.get("name") or "").strip(),
                        "part_cat_id": int(row["part_cat_id"]) if row.get("part_cat_id") else None,
                    }
                    _, was_created = RBPart.objects.update_or_create(part_num=part_num, defaults=defaults)
                    created += 1 if was_created else 0
                    updated += 0 if was_created else 1
            self.stdout.write(self.style.SUCCESS(f"Parts: +{created}, updated {updated}"))

        if opts["elements"]:
            self.stdout.write(self.style.MIGRATE_HEADING("Loading elements…"))
            to_create, seen = [], set()
            with _open(opts["elements"]) as f:
                for row in csv.DictReader(f):
                    element_id = (row["element_id"] or "").strip()
                    if not element_id or element_id in seen:
                        continue
                    seen.add(element_id)
                    part_num = (row["part_num"] or "").strip()
                    color_id = int(row["color_id"])
                    try:
                        part = RBPart.objects.get(pk=part_num)
                        color = RBColor.objects.get(pk=color_id)
                    except (RBPart.DoesNotExist, RBColor.DoesNotExist):
                        continue
                    to_create.append(RBElement(element_id=element_id, part=part, color=color))
                    if len(to_create) >= batch:
                        RBElement.objects.bulk_create(to_create, ignore_conflicts=True, batch_size=batch)
                        to_create.clear()
            if to_create:
                RBElement.objects.bulk_create(to_create, ignore_conflicts=True, batch_size=batch)
            self.stdout.write(self.style.SUCCESS("Elements: loaded (new elements inserted; existing kept)"))

        self.stdout.write(self.style.SUCCESS("Done."))
