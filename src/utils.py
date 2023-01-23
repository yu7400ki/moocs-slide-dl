import os
import shutil
import uuid
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
        extension = ext(response.content)
        path = os.path.join(dir, f"{uuid.uuid4()}.{extension}")
        with open(path, "wb") as f:
            f.write(response.content)
        return os.path.abspath(path)
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

    svg_path = os.path.join(dir, f"{uuid.uuid4()}.svg")
    pdf_path = os.path.join(dir, f"{uuid.uuid4()}.pdf")
    with open(svg_path, "w", encoding="UTF-8") as f:
        f.write(str(soup))

    drawing = svg2rlg(svg_path)
    renderPDF.drawToFile(drawing, pdf_path)

    os.remove(svg_path)
    for img_path in img_paths:
        if img_path:
            os.remove(img_path)

    return pdf_path


def fix(name: str) -> str:
    ban = ["\\", "/", ":", "*", "?", '"', "<", ">", "|"]
    return "".join([c for c in name if c not in ban])


def dl_slides(page: Page, out: str, temp: str):
    if os.path.exists(temp):
        shutil.rmtree(temp)

    write = os.path.join(out, fix(page.course), fix(page.group), fix(page.lecture))
    os.makedirs(write, exist_ok=True)
    slides = list(page.slides2svg())

    for i, slide in enumerate(slides):
        os.makedirs(temp)
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
        shutil.rmtree(temp)
