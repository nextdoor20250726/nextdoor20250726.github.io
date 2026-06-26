"""
Management command to add site_url field to all markdown frontmatter.
The URL follows the pattern:
  https://soundweavers-music.github.io/instruments/{filename-without-.md}/
"""
import os
import re
from django.conf import settings
from django.core.management.base import BaseCommand

FRONTMATTER_RE = re.compile(r"^(---\s*\n.*?\n---)", re.DOTALL)
SITE_URL_FIELD_RE = re.compile(r"^site_url:\s*", re.MULTILINE)
BASE_URL = "https://soundweavers-music.github.io"


class Command(BaseCommand):
    help = "Add site_url field to all instrument markdown files"

    def add_arguments(self, parser):
        parser.add_argument(
            "--md-dir",
            default="content/instruments",
            help="Path to markdown files directory",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be changed without writing",
        )

    def handle(self, *args, **options):
        md_dir = options["md_dir"]
        md_dir = os.path.join(settings.BASE_DIR, md_dir)
        dry_run = options["dry_run"]

        if not os.path.isdir(md_dir):
            self.stderr.write(f"Directory not found: {md_dir}")
            return

        updated = 0
        skipped = 0

        for filename in sorted(os.listdir(md_dir)):
            if not filename.endswith(".md"):
                continue
            filepath = os.path.join(md_dir, filename)
            basename = filename[:-3]  # remove .md
            site_url = f"{BASE_URL}/instruments/{basename}/"

            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            m = FRONTMATTER_RE.match(content)
            if not m:
                self.stdout.write(f"  [SKIP] No frontmatter: {filename}")
                skipped += 1
                continue

            frontmatter = m.group(1)

            if SITE_URL_FIELD_RE.search(frontmatter):
                self.stdout.write(f"  [SKIP] Already has site_url: {filename}")
                skipped += 1
                continue

            # Insert site_url after ---\n, keeping the opening --- intact
            new_fm = frontmatter.replace(
                "---\n", "---\nsite_url: " + site_url + "\n", 1
            )
            new_content = content.replace(frontmatter, new_fm, 1)

            if dry_run:
                self.stdout.write(f"  [DRY] Would add site_url to {filename}: {site_url}")
            else:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                self.stdout.write(f"  [OK] {filename} -> {site_url}")

            updated += 1

        self.stdout.write(f"\nDone: {updated} updated, {skipped} skipped")
