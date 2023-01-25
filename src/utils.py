import os
import tempfile
from concurrent.futures import ThreadPoolExecutor

import PyPDF2
import requests
from bs4 import BeautifulSoup
from iniad import Page
from reportlab.graphics import renderPDF
from svglib.svglib import svg2rlg


def ext(b: bytes) -> str:
    if b.startswith(b"\x89PNG"):
        return "png"
    elif b.startswith(b"\xff\xd8"):
        return "jpg"
    elif b.startswith(b"\x47\x49\x46\x38"):
        return "gif"
    elif b.startswith(b"\x42\x4d"):
        return "bmp"


def dl_img(url: str, dir: str):
    try:
        response = requests.get(url, timeout=3)
        content = response.content
        extension = ext(content)

        with tempfile.NamedTemporaryFile(suffix=f".{extension}", mode="wb", delete=False, dir=dir) as f:
            f.write(content)
            path = f.name

        return path
    except:
        return


def svg2pdf(svg: str, dir: str):
    img_paths = []
    soup = BeautifulSoup(svg, "xml")
    image = soup.select("image")

    for img in image:
        href = img.attrs["xlink:href"]
        img_path = dl_img(href, dir)
        img_paths.append(img_path)
        img.attrs["xlink:href"] = img_path if img_path else href

    with tempfile.NamedTemporaryFile(suffix=".svg", mode="w", encoding="UTF-8", delete=False, dir=dir) as f:
        f.write(str(soup))
        svg_path = f.name
        drawing = svg2rlg(svg_path)

        with tempfile.NamedTemporaryFile(suffix=".pdf", mode="wb", delete=False, dir=dir) as f:
            renderPDF.drawToFile(drawing, f.name)
            pdf_path = f.name

    return pdf_path


def fix(name: str) -> str:
    ban = ["\\", "/", ":", "*", "?", '"', "<", ">", "|"]
    return "".join([c for c in name if c not in ban])


def dl_slides(page: Page, out: str):
    write = os.path.join(out, fix(page.course), fix(page.group), fix(page.lecture))
    os.makedirs(write, exist_ok=True)
    slides = list(page.slides2svg())

    for i, slide in enumerate(slides):
        with tempfile.TemporaryDirectory(dir=out) as temp:
            futures = []
            if len(slides) > 1:
                print(f"Writing PDF...({page.course} - {page.lecture} - {page.name} - {i})")
            else:
                print(f"Writing PDF...({page.course} - {page.lecture} - {page.name})")
            with ThreadPoolExecutor(max_workers=8) as executor:
                for svg in slide:
                    future = executor.submit(svg2pdf, svg, temp)
                    futures.append(future)
            merger = PyPDF2.PdfMerger()
            [merger.append(future.result()) for future in futures]
            if len(slides) > 1:
                merger.write(os.path.join(write, f"{fix(page.name)}-{i}.pdf"))
            else:
                merger.write(os.path.join(write, f"{fix(page.name)}.pdf"))
            merger.close()
