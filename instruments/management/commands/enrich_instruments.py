"""
Management command to enrich Instrument data from markdown frontmatter.
Populates country, image_source fields and sets popular/uncommon flags.
"""
import os
import re
from django.conf import settings
from django.core.management.base import BaseCommand
from instruments.models import Instrument
from instruments.instrument_data import get_instrument_flags


FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


def parse_markdown_frontmatter(filepath):
    """Parse YAML-like frontmatter from a markdown file."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    m = FRONTMATTER_RE.match(content)
    if not m:
        return {}
    data = {}
    for line in m.group(1).split("\n"):
        line = line.strip()
        if ":" in line:
            key, _, value = line.partition(":")
            data[key.strip()] = value.strip()
    return data


class Command(BaseCommand):
    help = "Enrich instrument data from markdown frontmatter"

    def add_arguments(self, parser):
        parser.add_argument(
            "--markdown-dir",
            default="content/instruments",
            help="Path to markdown files directory",
        )

    def handle(self, *args, **options):
        md_dir = options["markdown_dir"]
        md_dir = os.path.join(settings.BASE_DIR, md_dir)

        if not os.path.isdir(md_dir):
            self.stderr.write(f"Markdown directory not found: {md_dir}")
            return

        updated_count = 0
        flagged_popular = 0
        flagged_uncommon = 0

        instruments = {inst.name: inst for inst in Instrument.objects.all()}

        for filename in sorted(os.listdir(md_dir)):
            if not filename.endswith(".md"):
                continue
            filepath = os.path.join(md_dir, filename)
            frontmatter = parse_markdown_frontmatter(filepath)

            title = frontmatter.get("title", "")
            original_name = frontmatter.get("original_name", "")
            country = frontmatter.get("country", "")
            image = frontmatter.get("image", "")

            # Try to match by original_name first, then title
            matched = None
            if original_name and original_name in instruments:
                matched = instruments[original_name]
            elif title and title in instruments:
                matched = instruments[title]

            # Fallback: try matching original_name case-insensitively
            if not matched and original_name:
                for name, inst in instruments.items():
                    if name.lower() == original_name.lower():
                        matched = inst
                        break

            if not matched:
                continue

            changed = False
            if country and not matched.country:
                matched.country = country
                changed = True

            if image and not matched.image_source:
                # Derive image source from Wikimedia URL
                if "upload.wikimedia.org" in image:
                    matched.image_source = "Wikimedia Commons"
                elif "wikipedia.org" in image:
                    matched.image_source = "Wikipedia"
                changed = True

            # Copy image from markdown to exploded_view_image if empty
            if image and not matched.exploded_view_image:
                matched.exploded_view_image = image
                changed = True

            # Set popular/uncommon flags
            lookup_names = [matched.name]
            if original_name:
                lookup_names.append(original_name)

            is_pop = False
            is_un = False
            for ln in lookup_names:
                p, u = get_instrument_flags(ln)
                if p:
                    is_pop = True
                if u:
                    is_un = True

            if is_pop and not matched.is_popular:
                matched.is_popular = True
                flagged_popular += 1
                changed = True
            if is_un and not matched.is_uncommon:
                matched.is_uncommon = True
                flagged_uncommon += 1
                changed = True

            if changed:
                matched.save(update_fields=["country", "image_source", "exploded_view_image", "is_popular", "is_uncommon"])
                updated_count += 1

        self.stdout.write(
            f"Updated {updated_count} instruments: "
            f"{flagged_popular} flagged popular, {flagged_uncommon} flagged uncommon"
        )
