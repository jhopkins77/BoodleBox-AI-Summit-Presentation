from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import tempfile
from html.parser import HTMLParser
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "presentation.html"
OUTPUT = ROOT / "BoodleBox_AI_Summit_Presentation.pptx"
VIEWPORT = (1280, 720)


class SlideParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.depth = 0
        self.top_level_count = 0
        self.child_counts: list[int] = []
        self.slides: list[tuple[int, int]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "section":
            return
        if self.depth == 0:
            self.top_level_count += 1
            self.child_counts.append(0)
        elif self.depth == 1:
            self.child_counts[-1] += 1
            self.slides.append((self.top_level_count - 1, self.child_counts[-1] - 1))
        self.depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "section" and self.depth:
            self.depth -= 1

    def coordinates(self) -> list[tuple[int, int]]:
        child_groups = {
            index for index, count in enumerate(self.child_counts) if count
        }
        slides = [
            coordinate
            for coordinate in self.slides
            if coordinate[0] in child_groups
        ]
        slides.extend(
            (index, 0)
            for index, count in enumerate(self.child_counts)
            if not count
        )
        return sorted(slides, key=lambda coordinate: (coordinate[0], coordinate[1]))


def find_chrome() -> str:
    for candidate in ("google-chrome", "chromium", "chromium-browser"):
        executable = shutil.which(candidate)
        if executable:
            return executable
    raise RuntimeError("Chrome or Chromium is required to export the slides.")


def render_slides(chrome: str, html_file: Path, images_dir: Path) -> list[Path]:
    parser = SlideParser()
    parser.feed(SOURCE.read_text(encoding="utf-8"))
    coordinates = parser.coordinates()
    if not coordinates:
        raise RuntimeError(f"No slides found in {SOURCE.name}.")

    rendered: list[Path] = []
    with tempfile.TemporaryDirectory(prefix="boodlebox-chrome-") as profile:
        for index, (horizontal, vertical) in enumerate(coordinates, start=1):
            image = images_dir / f"slide-{index:02}.png"
            url = f"{html_file.as_uri()}?export#/{horizontal}/{vertical}"
            subprocess.run(
                [
                    chrome,
                    "--headless",
                    "--no-sandbox",
                    "--disable-gpu",
                    "--hide-scrollbars",
                    f"--window-size={VIEWPORT[0]},{VIEWPORT[1]}",
                    f"--user-data-dir={profile}",
                    f"--screenshot={image}",
                    "--timeout=1500",
                    url,
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=60,
            )
            if not image.exists() or image.stat().st_size < 1_000:
                raise RuntimeError(f"Chrome did not render slide {index}.")
            rendered.append(image)
    return rendered


def create_presentation(images: list[Path], output: Path) -> None:
    presentation = Presentation()
    presentation.slide_width = Inches(13.333333)
    presentation.slide_height = Inches(7.5)
    blank_layout = presentation.slide_layouts[6]

    for image in images:
        slide = presentation.slides.add_slide(blank_layout)
        slide.shapes.add_picture(
            str(image),
            0,
            0,
            width=presentation.slide_width,
            height=presentation.slide_height,
        )

    presentation.save(output)


def main() -> None:
    argument_parser = argparse.ArgumentParser(
        description="Export the Reveal.js presentation to a sequential PowerPoint."
    )
    argument_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=OUTPUT,
        help=f"output PowerPoint path (default: {OUTPUT.name})",
    )
    args = argument_parser.parse_args()
    chrome = find_chrome()
    html_file = ROOT / ".presentation-pptx-export.html"
    original_html = SOURCE.read_text(encoding="utf-8")
    export_html = re.sub(
        r"<iframe\b[^>]*>.*?</iframe>",
        '<div class="pptx-embed-placeholder">Interactive activity'
        "<br><small>Participate using the online presentation.</small></div>",
        original_html,
        flags=re.DOTALL,
    )
    export_html = export_html.replace(
        "</head>",
        "<style>"
        ".reveal .controls,.reveal .progress{display:none!important}"
        ".pptx-embed-placeholder{position:absolute;inset:0;display:grid;"
        "place-content:center;padding:1rem;background:#1e293b;color:#f8fafc;"
        "font:600 1rem/1.5 'Segoe UI',sans-serif;text-align:center}"
        ".pptx-embed-placeholder small{color:#cbd5e1;font-weight:400}"
        "</style>\n"
        "</head>",
        1,
    )

    if export_html == original_html:
        raise RuntimeError(f"Could not prepare {SOURCE.name} for export.")

    try:
        html_file.write_text(export_html, encoding="utf-8")
        with tempfile.TemporaryDirectory(prefix="boodlebox-slides-") as temporary:
            images = render_slides(chrome, html_file, Path(temporary))
            create_presentation(images, args.output.resolve())
    finally:
        html_file.unlink(missing_ok=True)

    print(f"Wrote {args.output} with {len(images)} slides.")


if __name__ == "__main__":
    main()
