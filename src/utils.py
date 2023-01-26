import base64
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

import requests
from bs4 import BeautifulSoup
from iniad import Page


def ext(b: bytes) -> str:
    if b.startswith(b"\x89PNG"):
        return "png"
    elif b.startswith(b"\xff\xd8"):
        return "jpg"
    elif b.startswith(b"\x47\x49\x46\x38"):
        return "gif"
    elif b.startswith(b"<?xml") or b.startswith(b"<svg"):
        return "svg"
    else:
        raise ValueError("Unknown image format")


def fix(name: str) -> str:
    ban = ["\\", "/", ":", "*", "?", '"', "<", ">", "|"]
    return "".join([c for c in name if c not in ban]).strip()


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
                        future = executor.submit(self.process, svg)
                        futures.append(future)
                title = f"{fix(self.page.name)}-{i}" if len(self.slides) > 1 else f"{fix(self.page.name)}"
                template_soup = BeautifulSoup(html_template, "html.parser")
                title_elm = template_soup.select_one("title")
                slide_elm = template_soup.select_one("div#slide-container")
                title_elm.append(title)
                for future in futures:
                    result = future.result()
                    section = template_soup.new_tag("section")
                    section.append(result)
                    slide_elm.append(section)
                html = str(template_soup)
                path = os.path.join(self.write, f"{title}.html")
                with open(path, "w", encoding="UTF-8") as f:
                    f.write(html)

    def process(self, svg: str):
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

        svg_elm = soup.select_one("svg")
        return svg_elm

    def dl_img(self, href: str) -> str:
        try:
            response = requests.get(href, timeout=3)
            content = response.content
            extension = ext(content)
            encoded = base64.b64encode(content)

            if extension in ("jpg", "png", "gif"):
                image = f"data:image/{extension};base64,{encoded.decode('utf-8')}"
            elif extension == "svg":
                image = f"data:image/svg+xml;base64,{encoded.decode('utf-8')}"
            else:
                raise ValueError("Unknown image format")

            return image
        except:
            return


html_template = """<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8"><meta http-equiv="X-UA-Compatible" content="IE=edge"><meta name="viewport" content="width=device-width,initial-scale=1"><title></title></head><style>header,header>div{align-items:center}header>div,nav{gap:10px;display:flex}#page-num>input,body,header button,html,nav>button{color:var(--color-primary)}body,html,main{background-color:var(--color-main)}main,nav{padding:30px 0;height:calc(100vh - 50px);overflow-y:auto}header,header button,header>div,nav{display:flex}*,::after,::before{box-sizing:border-box;margin:0}:root.dark{color-scheme:dark;--color-header:#3b3b3b;--color-main:#333333;--color-sidebar:#4a4a4a;--color-primary:white;--color-accent:#5fb8e4}:root.light{color-scheme:light;--color-header:#f7f7f7;--color-main:#dfdfdf;--color-sidebar:#eeeeee;--color-primary:black;--color-accent:#5fb8e4}body,html{height:100vh;width:100%;line-height:1.5}button,input{background-color:transparent;border:none;outline:0;padding:0;appearance:none;font:inherit}button{cursor:pointer}.grid{display:grid;grid-template-columns:max(250px,min(20%,350px)) 1fr;grid-template-rows:50px 1fr;min-height:100vh}.hide-contents{grid-template-columns:0 1fr}header{background-color:var(--color-header);grid-column:1/3;justify-content:space-between;padding:0 25px}header>div{height:35px}header button{align-items:center;justify-content:center;border-radius:5px;height:100%;width:35px}#sidebar,header button:hover{background-color:var(--color-sidebar)}#page-num{height:100%}#page-num>input{width:50px;border:1px solid #6a6a6b;border-radius:5px;height:100%;text-align:right;padding:0 10px}#slide-container>section,.preview{width:100%}#page-num>span::before{content:"/ ";margin-left:5px}nav{flex-direction:column;align-items:center;overflow-x:hidden}nav>button{width:75%;font-size:14px;opacity:.7}.preview{box-sizing:content-box;line-height:0;position:relative;margin-bottom:8px;filter:drop-shadow(0 0 5px rgba(0, 0, 0, .2));border:5px solid transparent}nav>button.active{opacity:1}nav>button.active>.preview{border:solid 5px var(--color-accent)}main{flex-grow:1;overflow-x:auto}#slide-container{display:flex;flex-direction:column;align-items:center;gap:30px;margin:0 auto}</style><body><div class="grid"><header><div id="contents-control"><button type="button" id="toggle-contents" aria-label="目次"><svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-align-justified" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round"><path stroke="none" d="M0 0h24v24H0z" fill="none"></path><path d="M4 6l16 0m-16 6l16 0m-16 6l12 0"></path></svg></button><div id="page-num"><input type="text" value="1"><span></span></div></div><div id="zoom"><button type="button" id="zoom-out" aria-label="ズームアウト"><svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-minus" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round"><path stroke="none" d="M0 0h24v24H0z" fill="none"></path><path d="M5 12l14 0"></path></svg></button><button type="button" id="zoom-in" aria-label="ズームイン"><svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-plus" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round"><path stroke="none" d="M0 0h24v24H0z" fill="none"></path><path d="M12 5l0 14m-7 -7l14 0"></path></svg></button><button type="button" id="fill" aria-label="画面幅に合わせる"><svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-arrow-autofit-width" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round"><path stroke="none" d="M0 0h24v24H0z" fill="none"></path><path d="M4 12v-6a2 2 0 0 1 2 -2h12a2 2 0 0 1 2 2v6m-10 6h-7m18 0h-7m-8 -3l-3 3l3 3m12 -6l3 3l-3 3"></path></svg></button></div><div id="other"><button type="button" id="dark-mode" aria-label="ダークモード"><svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-moon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round"><path stroke="none" d="M0 0h24v24H0z" fill="none"></path><path d="M12 3c.132 0 .263 0 .393 0a7.5 7.5 0 0 0 7.92 12.446a9 9 0 1 1 -8.313 -12.454z"></path></svg></button><button type="button" id="light-mode" aria-label="ライトモード"><svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-moon-off" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round"><path stroke="none" d="M0 0h24v24H0z" fill="none"></path><path d="M7.962 3.949a8.97 8.97 0 0 1 4.038 -.957v.008h.393a7.478 7.478 0 0 0 -2.07 3.308m-.141 3.84c.186 .823 .514 1.626 .989 2.373a7.49 7.49 0 0 0 4.586 3.268m3.893 -.11c.223 -.067 .444 -.144 .663 -.233a9.088 9.088 0 0 1 -.274 .597m-1.695 2.337a9 9 0 0 1 -12.71 -12.749m-2.634 -2.631l18 18"></path></svg></button></div></header><div id="sidebar"><nav id="contents"></nav></div><main><div id="slide-container"></div></main></div></body><script>const toggleContentsButton=document.querySelector("#toggle-contents"),gridContainer=document.querySelector(".grid");toggleContentsButton.addEventListener("click",()=>{gridContainer.classList.toggle("hide-contents")});const offset=30,scrollNav=e=>{let t=document.querySelector("nav"),n=t.getBoundingClientRect(),o=e.getBoundingClientRect();o.top<n.top?t.scrollBy({top:o.top-n.top-30,behavior:"instant"}):o.bottom>n.bottom&&t.scrollBy({top:o.bottom-n.bottom+30,behavior:"instant"})},main=document.querySelector("main"),mainRect=main.getBoundingClientRect(),slides=document.querySelectorAll("main > div > section"),nav=document.querySelector("nav"),pageInput=document.querySelector("#page-num > input"),pageSpan=document.querySelector("#page-num > span");pageSpan.textContent=slides.length;let prevPage=1;for(let i=0;i<slides.length;i++){let e=slides[i],t=document.createElement("button"),n=e.cloneNode(!0);n.classList.add("preview"),t.setAttribute("type","button"),t.setAttribute("aria-label",`${i+1}ページ目`),t.appendChild(n),t.appendChild(document.createTextNode(`${i+1}`)),t.addEventListener("click",()=>{let n=e.getBoundingClientRect();main.scrollBy({top:n.top-mainRect.top-mainRect.height/2+n.height/2,behavior:"instant"}),prevPage=i+1,pageInput.value=i+1,scrollNav(t)}),nav.appendChild(t)}const navChildren=nav.querySelectorAll("button"),options={root:null,rootMargin:"-50% 0px",threshold:0},observer=new IntersectionObserver(e=>{e.forEach(e=>{if(!e.isIntersecting)return;let t=Array.from(slides).indexOf(e.target);navChildren.forEach(e=>e.classList.remove("active")),navChildren[t].classList.add("active"),prevPage=t+1,pageInput.value=t+1,scrollNav(navChildren[t])})},options);slides.forEach(e=>{observer.observe(e)}),pageInput.addEventListener("keydown",e=>{if("Enter"!==e.key)return;let t=parseInt(pageInput.value,10);if(isNaN(t)){pageInput.value=prevPage;return}t<1&&(t=1),t>slides.length&&(t=slides.length),navChildren[t-1].click()}),pageInput.addEventListener("change",()=>{pageInput.value=prevPage});const darkModeButton=document.querySelector("#dark-mode"),lightModeButton=document.querySelector("#light-mode"),isDarkMode=window.matchMedia("(prefers-color-scheme: dark)").matches,switchMode=e=>{"dark"===e?(document.documentElement.classList.remove("light"),document.documentElement.classList.add("dark"),darkModeButton.style.display="none",lightModeButton.style.display="flex"):(document.documentElement.classList.remove("dark"),document.documentElement.classList.add("light"),darkModeButton.style.display="flex",lightModeButton.style.display="none")};isDarkMode?switchMode("dark"):switchMode("light"),darkModeButton.addEventListener("click",()=>{switchMode("dark")}),lightModeButton.addEventListener("click",()=>{switchMode("light")});const slideContainer=document.querySelector("#slide-container"),zoomInButton=document.querySelector("#zoom-in"),zoomOutButton=document.querySelector("#zoom-out"),fillButton=document.querySelector("#fill"),defaultWidth=mainRect.width;let scale=.9;const zoom=e=>{slideContainer.style.width=`${defaultWidth*e}px`};zoom(scale),zoomInButton.addEventListener("click",()=>{(scale+=.1)>2&&(scale=2),zoom(scale)}),zoomOutButton.addEventListener("click",()=>{(scale-=.1)<.1&&(scale=.1),zoom(scale)}),fillButton.addEventListener("click",()=>{slideContainer.style.width="100%"});</script></html>"""
