import sys

import PySimpleGUI as sg
from iniad import Moocs

text_width = 8
input_width = 50
text_height = input_height = 1
text_size = (text_width, text_height)
combo_size = (input_width, input_height)
font = ("Helvetica", 12)


class LoginPopup:
    def __init__(self):
        self.layout = [
            [
                sg.Text("Username", size=text_size, font=font),
                sg.InputText(key="username", size=combo_size, font=font),
            ],
            [
                sg.Text("Password", size=text_size, font=font),
                sg.InputText(key="password", password_char="*", size=combo_size, font=font),
            ],
            [sg.Text(" ", font=font)],
            [sg.Button("Login", font=font), sg.Button("Cancel", font=font)],
        ]

    def show(self):
        window = sg.Window("Login", self.layout)
        while True:
            event, values = window.read()
            match event:
                case sg.WIN_CLOSED | "Cancel":
                    sys.exit()
                case "Login":
                    try:
                        moocs = Moocs(values["username"], values["password"])
                        moocs.login_google()
                        break
                    except:
                        sg.popup_error("Login failed")
                case _:
                    continue
        window.close()
        return moocs
