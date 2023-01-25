import base64
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

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
    else:
        raise ValueError("Unknown image format")


def fix(name: str) -> str:
    ban = ["\\", "/", ":", "*", "?", '"', "<", ">", "|"]
    return "".join([c for c in name if c not in ban])


@dataclass
class DLSlides:
    page: Page
    out: str
    downloaded_img: dict[str:str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.write = os.path.join(self.out, fix(self.page.course), fix(self.page.group), fix(self.page.lecture))
        os.makedirs(self.write, exist_ok=True)
        self.slides = list(self.page.slides2svg())

        with tempfile.TemporaryDirectory(dir=self.out) as self.temp:
            for i, slide in enumerate(self.slides):
                futures = []
                with ThreadPoolExecutor(max_workers=8) as executor:
                    for svg in slide:
                        future = executor.submit(self.svg2pdf, svg)
                        futures.append(future)
                merger = PyPDF2.PdfMerger()
                [merger.append(future.result()) for future in futures]
                if len(self.slides) > 1:
                    merger.write(os.path.join(self.write, f"{fix(self.page.name)}-{i}.pdf"))
                else:
                    merger.write(os.path.join(self.write, f"{fix(self.page.name)}.pdf"))
                merger.close()

    def svg2pdf(self, svg: str) -> str:
        soup = BeautifulSoup(svg, "xml")
        image = soup.select("image")

        for img in image:
            href = img.attrs["xlink:href"]
            if href in self.downloaded_img:
                image = self.downloaded_img[href]
            else:
                image = self.dl_img(href)
                self.downloaded_img[href] = image
            img.attrs["xlink:href"] = image if image else href

        with tempfile.NamedTemporaryFile(suffix=".svg", mode="w", encoding="UTF-8", delete=False, dir=self.temp) as f:
            f.write(str(soup))
            svg_path = f.name
            drawing = svg2rlg(svg_path)

        with tempfile.NamedTemporaryFile(suffix=".pdf", mode="wb", delete=False, dir=self.temp) as f:
            renderPDF.drawToFile(drawing, f.name)
            pdf_path = f.name

        return pdf_path

    def dl_img(self, href: str) -> str:
        try:
            response = requests.get(href, timeout=3)
            content = response.content
            extension = ext(content)

            if extension in ("jpg", "png"):
                encoded = base64.b64encode(content)
                image = f"data:image/{extension};base64,{encoded.decode('utf-8')}"
            else:
                with tempfile.NamedTemporaryFile(suffix=f".{extension}", mode="wb", delete=False, dir=self.temp) as f:
                    f.write(content)
                    image = f.name

            return image
        except:
            return
