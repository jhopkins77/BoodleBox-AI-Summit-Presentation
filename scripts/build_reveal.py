from __future__ import annotations

import html
import shutil
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "original_pptx" / "Bryn_Mawr_Virtual_TAs_Presentation_Final.pptx"
OUTPUT = ROOT / "boodlebox-ai-summit.html"
IMAGES = ROOT / "images"

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}

PEOPLE = {
    "ARBioPic.jpg": "ARBioPic.jpg",
    "CBBioPic.jpg": "CBBioPic.jpg",
    "EABioPic.jpeg": "EABioPic.jpeg",
    "GDBioPic.jpg": "GDBioPic.jpg",
    "JSBioPic.jpg": "JSBioPic.jpg",
    "PSBioPic.jpeg": "PSBioPic.jpeg",
    "XCBioPic.jpg": "XCBioPic.jpg",
    "YDarBioPic.jpeg": "YDarBioPic.jpeg",
}


def shape_paragraphs(shape: ET.Element) -> list[str]:
    result: list[str] = []
    for paragraph in shape.findall("./p:txBody/a:p", NS):
        pieces: list[str] = []
        for node in paragraph:
            if node.tag == f"{{{NS['a']}}}br":
                pieces.append("\n")
            elif node.tag in (f"{{{NS['a']}}}r", f"{{{NS['a']}}}fld"):
                pieces.extend(item.text or "" for item in node.findall(".//a:t", NS))
        value = "".join(pieces)
        if value:
            result.append(value)
    return result


def read_slides() -> list[list[list[str]]]:
    slides: list[list[list[str]]] = []
    with zipfile.ZipFile(SOURCE) as presentation:
        for index in range(1, 26):
            root = ET.fromstring(presentation.read(f"ppt/slides/slide{index}.xml"))
            shapes = root.findall("./p:cSld/p:spTree/p:sp", NS)
            slides.append([paragraphs for shape in shapes if (paragraphs := shape_paragraphs(shape))])
        for name in ("image1.png", "image2.jpg"):
            (IMAGES / name).write_bytes(presentation.read(f"ppt/media/{name}"))
    return slides


def copy_people() -> None:
    IMAGES.mkdir(exist_ok=True)
    for source_name, target_name in PEOPLE.items():
        shutil.copy2(ROOT / "original_pptx" / source_name, IMAGES / target_name)


def text(value: str) -> str:
    return html.escape(value, quote=False).replace("\n", "<br>")


def paragraphs(values: list[str], class_name: str = "") -> str:
    class_attr = f' class="{class_name}"' if class_name else ""
    return f"<div{class_attr}>" + "".join(f"<p>{text(value)}</p>" for value in values) + "</div>"


def image(src: str, alt: str, class_name: str = "") -> str:
    class_attr = f' class="{class_name}"' if class_name else ""
    return f'<img{class_attr} src="{html.escape(src, quote=True)}" alt="{html.escape(alt, quote=True)}">'


def header(paras: list[str]) -> str:
    if len(paras) > 1:
        return (
            '<header class="slide-header">'
            f'<p class="eyebrow">{text(paras[0])}</p>'
            f"<h2>{text(paras[1])}</h2>"
            "</header>"
        )
    return f'<header class="slide-header"><h2>{text(paras[0])}</h2></header>'


def card(title: str, body: list[str], class_name: str = "") -> str:
    class_attr = f" {class_name}" if class_name else ""
    title_html = f"<h3>{text(title)}</h3>" if title else ""
    return f'<article class="card{class_attr}">{title_html}{paragraphs(body, "card-copy")}</article>'


def figure(src: str, alt: str, caption: str, class_name: str = "") -> str:
    class_attr = f' class="{class_name}"' if class_name else ""
    return (
        f"<figure{class_attr}>{image(src, alt)}"
        f"<figcaption>{text(caption)}</figcaption></figure>"
    )


def split_header_block(paras: list[str]) -> tuple[str, str, list[str]]:
    return paras[0], paras[1], paras[2:]


def render(slides: list[list[list[str]]]) -> str:
    rendered: list[str] = []

    first = slides[0][0]
    rendered.append(
        '<section class="slide cover">'
        f"<h1>{text(first[0])}</h1>"
        f'<p class="cover-subtitle">{text(first[1])}</p>'
        f'<p class="cover-credit">{text(first[2])}</p>'
        "</section>"
    )

    for number, blocks in enumerate(slides[1:], start=2):
        if number in {10, 12, 14, 17, 21, 23, 24}:
            value = blocks[0][0]
            audience = "Faculty perspective" if value.startswith("Faculty perspective") else "Student Perspective"
            question = value[len(audience):]
            rendered.append(
                f'<section class="slide perspective {"faculty" if audience.startswith("Faculty") else "student"}">'
                f'<p class="perspective-label">{text(audience)}</p>'
                f'<h2>{text(question)}</h2></section>'
            )
            continue

        if number in {2, 3, 20}:
            title = blocks[0][0]
            body = blocks[1]
            rendered.append(
                f'<section class="slide prompt-slide prompt-{number}">'
                f'<h2>{text(title)}</h2>{paragraphs(body, "prompt-copy")}</section>'
            )
            continue

        title_block = blocks[0]
        body_blocks = blocks[1:]
        if number == 4:
            name, role, *details = body_blocks[0]
            content = (
                '<div class="profile-layout"><article class="card profile-copy">'
                f"<h3>{text(name)}</h3><p class=\"role\">{text(role)}</p>"
                f"{paragraphs(details, 'card-copy')}"
                "</article>"
                f'<div class="portrait">{image("images/image1.png", "Photo from the PowerPoint")}</div></div>'
            )
        elif number == 5:
            content = (
                '<div class="split-layout"><article class="card large-copy">'
                f"{paragraphs(body_blocks[0], 'card-copy')}</article>"
                f'<div class="campus-image">{image("images/image2.jpg", "Bryn Mawr College campus")}</div></div>'
            )
        elif number == 6:
            cards = "".join(
                card(block[0], block[1:], "agenda-card") for block in body_blocks
            )
            content = f'<div class="agenda-grid">{cards}</div>'
        elif number == 7:
            caption = body_blocks[1][0]
            content = (
                '<div class="split-layout"><article class="card large-copy">'
                f"{paragraphs(body_blocks[0], 'card-copy')}</article>"
                '<div class="photo-pair">'
                f'{image("images/CBBioPic.jpg", "Chris Barth portrait")}'
                f'{image("images/JSBioPic.jpg", "Jenny Spohrer portrait")}'
                f"<p>{text(caption)}</p></div></div>"
            )
        elif number == 8:
            people = [
                ([("GDBioPic.jpg", "Greg Davis portrait")], body_blocks[0][0], body_blocks[1]),
                ([("EABioPic.jpeg", "Evan Arena portrait"), ("XCBioPic.jpg", "Xuemei Cheng portrait")], body_blocks[2][0], body_blocks[3]),
                ([("ARBioPic.jpg", "Asja Radja portrait")], body_blocks[4][0], body_blocks[5]),
            ]
            cards = []
            for photos, label, details in people:
                photo_images = "".join(
                    image(f"images/{filename}", alt) for filename, alt in photos
                )
                cards.append(
                    '<article class="card person-card">'
                    f'<div class="person-photos">{photo_images}</div>'
                    f"<p class=\"photo-label\">{text(label)}</p>"
                    f"<h3>{text(details[0])}</h3>"
                    f'<p class="role">{text(details[1])}</p>'
                    f"{paragraphs(details[2:], 'card-copy')}</article>"
                )
            content = f'<div class="people-grid">{ "".join(cards) }</div>'
        elif number == 9:
            cards = "".join(
                card(block[0], block[1:], "goal-card") for block in body_blocks
            )
            content = f'<div class="goal-grid">{cards}</div>'
        elif number == 11:
            main, sidenote, photo_one, person_one, photo_two, person_two = body_blocks
            right_cards = []
            for filename, alt, caption, info in (
                ("PSBioPic.jpeg", "Pragya Silwal portrait", photo_one[0], person_one),
                ("YDarBioPic.jpeg", "Yumna Fatima Dar portrait", photo_two[0], person_two),
            ):
                right_cards.append(
                    '<article class="card student-card">'
                    f'{image(f"images/{filename}", alt)}'
                    f"<p class=\"photo-label\">{text(caption)}</p>"
                    f"<h3>{text(info[0])}</h3>{paragraphs(info[1:], 'card-copy')}</article>"
                )
            content = (
                '<div class="intern-layout"><div class="intern-copy">'
                f'<article class="card"><h3>{text(main[0])}</h3>{paragraphs(main[1:], "card-copy")}</article>'
                f'<article class="card sidenote">{paragraphs(sidenote, "card-copy")}</article>'
                f'</div><div class="student-grid">{"".join(right_cards)}</div></div>'
            )
        elif number == 13:
            cards = "".join(
                f'<article class="step-card"><h3>{text(block[0])}</h3>'
                f"{paragraphs(block[1:], 'card-copy')}</article>"
                for block in body_blocks
            )
            content = f'<div class="steps-grid">{cards}</div>'
        elif number == 15:
            body, placeholder = body_blocks
            content = (
                '<div class="split-layout"><article class="card large-copy">'
                f"{paragraphs(body, 'card-copy')}</article>"
                f'<div class="screenshot-placeholder">{text(placeholder[0])}</div></div>'
            )
        elif number == 16:
            cards = "".join(
                card(block[0], block[1:], "tool-card") for block in body_blocks
            )
            content = f'<div class="tool-grid">{cards}</div>'
        elif number == 18:
            cards = "".join(
                f'<article class="card challenge-card">{paragraphs([item], "card-copy")}</article>'
                for item in body_blocks[0]
            )
            content = f'<div class="challenge-grid">{cards}</div>'
        elif number == 19:
            labels = [
                "[ Graph / Stats: Quant Assistant Usage ]",
                "[ Graph / Stats: Phys121 Usage ]",
                "[ Preview / Screenshot: BIOL 202 TA ]",
            ]
            cards = []
            for idx, label in enumerate(labels):
                copy_block = body_blocks[idx * 2 + 1]
                cards.append(
                    f'<article class="card rollout-card"><div class="plot-placeholder">{text(label)}</div>'
                    f"<h3>{text(copy_block[0])}</h3>"
                    f'<p class="role">{text(copy_block[1])}</p>'
                    f"{paragraphs(copy_block[2:], 'card-copy')}</article>"
                )
            content = f'<div class="rollout-grid">{"".join(cards)}</div>'
        elif number == 22:
            columns = "".join(
                f'<article class="card takeaway-card"><h3>{text(block[0])}</h3>'
                f"{paragraphs(block[1:], 'card-copy')}</article>"
                for block in body_blocks
            )
            content = f'<div class="takeaways-grid">{columns}</div>'
        elif number == 25:
            closing = title_block
            content = (
                '<div class="closing-copy">'
                f"<h1>{text(closing[0])}</h1>"
                f"<h2>{text(closing[1])}</h2>"
                f"<p>{text(closing[2])}</p></div>"
            )
            rendered.append(
                f'<section class="slide content-slide slide-{number}">'
                f'<div class="slide-content">{content}</div></section>'
            )
            continue
        else:
            content = paragraphs([value for block in body_blocks for value in block], "card-copy")

        rendered.append(
            f'<section class="slide content-slide slide-{number}">{header(title_block)}'
            f'<div class="slide-content">{content}</div></section>'
        )

    return """<!doctype html>
<html lang="en">
<head>
\t<meta charset="utf-8">
\t<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
\t<title>BoodleBox AI Summit Presentation</title>
\t<link rel="stylesheet" href="dist/reset.css">
\t<link rel="stylesheet" href="dist/reveal.css">
\t<link rel="stylesheet" href="dist/theme/night.css">
\t<link rel="stylesheet" href="plugin/highlight/monokai.css">
\t<link rel="stylesheet" href="css/boodle-summit.css">
</head>
<body>
\t<div class="reveal"><div class="slides">
""" + "\n".join(rendered) + """
\t</div></div>
\t<script src="dist/reveal.js"></script>
\t<script src="plugin/notes/notes.js"></script>
\t<script src="plugin/markdown/markdown.js"></script>
\t<script src="plugin/highlight/highlight.js"></script>
\t<script>
\t\tReveal.initialize({
\t\t\thash: true,
\t\t\tplugins: [ RevealMarkdown, RevealHighlight, RevealNotes ]
\t\t});
\t</script>
</body>
</html>
"""


def main() -> None:
    copy_people()
    slides = read_slides()
    OUTPUT.write_text(render(slides), encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)} with {len(slides)} slides and {len(PEOPLE) + 2} images.")


if __name__ == "__main__":
    main()
