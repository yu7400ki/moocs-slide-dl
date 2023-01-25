import os
import platform
import time

import PySimpleGUI as sg
from iniad import Course, Lecture, Moocs, Page
from win11toast import toast

from login import LoginPopup
from utils import DLSlides

APP_NAME = "Moocs Slide Downloader"

text_width = 10
combo_width = 50
button_width = 8
output_width = text_width + combo_width + 1
output_height = 20

text_height = combo_height = input_height = 1
text_size = (text_width, text_height)
combo_size = (combo_width, combo_height)
input_size = (combo_width - button_width, input_height)
button_size = (button_width, input_height)
output_size = (output_width, output_height)
font = ("Helvetica", 12)

layout = [
    [
        sg.Text("Course", size=text_size, font=font),
        sg.Combo(
            values=["All"],
            key="course",
            enable_events=True,
            size=combo_size,
            font=font,
            default_value="All",
            disabled=True,
        ),
    ],
    [
        sg.Text("Group", size=text_size, font=font),
        sg.Combo(
            values=["All"],
            key="group",
            enable_events=True,
            size=combo_size,
            font=font,
            default_value="All",
            disabled=True,
        ),
    ],
    [
        sg.Text("Lecture", size=text_size, font=font),
        sg.Combo(
            values=["All"],
            key="lecture",
            enable_events=True,
            size=combo_size,
            font=font,
            default_value="All",
            disabled=True,
        ),
    ],
    [
        sg.Text("Page", size=text_size, font=font),
        sg.Combo(
            values=["All"],
            key="page",
            enable_events=True,
            size=combo_size,
            font=font,
            default_value="All",
            disabled=True,
        ),
    ],
    [
        sg.Text("Output", size=text_size, font=font),
        sg.InputText(key="output", size=input_size, font=font),
        sg.FolderBrowse(target="output", size=button_size, font=font),
    ],
    [
        sg.Output(size=output_size, font=font),
    ],
    [
        sg.Button("Download", size=button_size, font=font, key="download"),
    ],
]


def download(selected_course, selected_group, selected_lecture, selected_page, courses, groups, pages, window, output):
    window["download"].Update(disabled=True)
    if selected_course == "All":
        for course in courses.values():
            for lecture in course.lectures():
                for page in lecture.pages():
                    DLSlides(page, output)
                    time.sleep(1)
    elif selected_group == "All":
        course = courses[selected_course]
        for lecture in course.lectures():
            for page in lecture.pages():
                DLSlides(page, output)
                time.sleep(1)
    elif selected_lecture == "All":
        lectures = groups[selected_group]
        for lecture in lectures.values():
            for page in lecture.pages():
                DLSlides(page, output)
                time.sleep(1)
    elif selected_page == "All":
        lecture = groups[selected_group][selected_lecture]
        for page in lecture.pages():
            DLSlides(page, output)
            time.sleep(1)
    else:
        page = pages[selected_page]
        DLSlides(page, output)
    window["download"].Update(disabled=False)


if __name__ == "__main__":
    moocs: Moocs = LoginPopup().show()
    window = sg.Window("Download", layout, finalize=True)
    courses: dict[str:Course] = {course.name: course for course in moocs.courses()}
    groups: dict[str : dict[str:Lecture]] = {}
    pages: dict[str:Page] = {}
    window["course"].Update(values=["All"] + [key for key in courses.keys()], disabled=False, value="All")

    while True:
        event, values = window.read()

        match event:
            case sg.WIN_CLOSED:
                break

            case "course":
                selected_course: str = values["course"]

                match selected_course:
                    case "All":
                        window["group"].Update(values=["All"], disabled=True, value="All")
                    case _:
                        course = courses[selected_course]
                        lectures = course.lectures()
                        groups.clear()
                        for lecture in lectures:
                            if lecture.group not in groups:
                                groups[lecture.group] = {}
                            groups[lecture.group][lecture.name] = lecture
                        window["group"].Update(
                            values=["All"] + [key for key in groups.keys()], disabled=False, value="All"
                        )

                window["lecture"].Update(values=["All"], disabled=True, value="All")
                window["page"].Update(values=["All"], disabled=True, value="All")

            case "group":
                selected_group: str = values["group"]

                match selected_group:
                    case "All":
                        window["lecture"].Update(values=["All"], disabled=True, value="All")
                    case _:
                        lectures = groups[selected_group]
                        window["lecture"].Update(
                            values=["All"] + [key for key in lectures.keys()], disabled=False, value="All"
                        )

                window["page"].Update(values=["All"], disabled=True, value="All")

            case "lecture":
                selected_lecture: str = values["lecture"]
                selected_group: str = values["group"]

                match selected_lecture:
                    case "All":
                        window["page"].Update(values=["All"], disabled=True, value="All")
                    case _:
                        lecture: Lecture = groups[selected_group][selected_lecture]
                        pages = {page.name: page for page in lecture.pages()}
                        window["page"].Update(
                            values=["All"] + [key for key in pages.keys() if pages[key].slides],
                            disabled=False,
                            value="All",
                        )

            case "page":
                pass

            case "download":
                output = values["output"]
                if not os.path.isdir(output):
                    sg.popup_error("Output directory does not exist")
                    continue

                selected_course: str = values["course"]
                selected_group: str = values["group"]
                selected_lecture: str = values["lecture"]
                selected_page: str = values["page"]

                window.start_thread(
                    lambda: download(
                        selected_course,
                        selected_group,
                        selected_lecture,
                        selected_page,
                        courses,
                        groups,
                        pages,
                        window,
                        output,
                    ),
                    "-THREAD ENDED-",
                )

            case "-THREAD ENDED-":
                if platform.system() == "Windows":
                    window.start_thread(
                        lambda: toast("Download finished", app_id=APP_NAME, on_click=lambda _: window.BringToFront()),
                        "-",
                    )
                sg.popup("Download finished")

            case _:
                continue

    window.close()
