import platform
import threading
import tkinter as tk
import tkinter.ttk as ttk
from sys import exit
from typing import Literal

import win32.lib.win32con as win32con
import win32gui
from components.MBox import Mbox
from components.Tooltip import CreateToolTip
from Globals import app_icon, app_icon_missing, app_name, fJson, gClass, version
from notifypy import Notify, exceptions
from PIL import Image, ImageDraw
from pystray import Icon as icon
from pystray import Menu as menu
from pystray import MenuItem as item
from utils.Helper import modelKeys, modelSelectDict, upFirstCase
from utils.LangCode import engine_select_source_dict, engine_select_target_dict, whisper_compatible
from utils.Record import getInputDevice, getOutputDevice, rec_mic


def hideConsole(win):
    if win is not None:
        win32gui.ShowWindow(win, win32con.SW_HIDE)


def showConsole(win):
    if win is not None:
        win32gui.ShowWindow(win, win32con.SW_SHOW)


class AppTray:
    """
    Tray app
    """

    def __init__(self):
        self.icon: icon = None  # type: ignore
        self.menu: menu = None  # type: ignore
        self.menu_items: tuple[item, item] = None  # type: ignore
        gClass.tray = self  # type: ignore
        self.create_tray()

    # -- Tray icon
    def create_image(self, width, height, color1, color2):
        # Generate an image and draw a pattern
        image = Image.new("RGB", (width, height), color1)
        dc = ImageDraw.Draw(image)
        dc.rectangle((width // 2, 0, width, height // 2), fill=color2)
        dc.rectangle((0, height // 2, width // 2, height), fill=color2)

        return image

    # -- Create tray
    def create_tray(self):
        trayIco = Image.open(app_icon) if not app_icon_missing else self.create_image(64, 64, "black", "white")
        self.menu_items = (item("Show", self.open_app), item("Exit", self.exit_app))
        self.menu = menu(*self.menu_items)
        self.icon = icon("Speech Translate", trayIco, f"Speech Translate V{version}", self.menu)
        self.icon.run_detached()

    # -- Open app
    def open_app(self):
        assert gClass.mw is not None  # Show main window
        gClass.mw.show_window()

    # -- Exit app by flagging runing false to stop main loop
    def exit_app(self):
        gClass.running = False


class MainWindow:
    """
    Main window of the app
    """

    def __init__(self):
        # ------------------ Window ------------------
        # UI
        self.root = tk.Tk()

        self.root.title(f"Speech Translate")
        self.root.geometry("1200x400")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.wm_attributes("-topmost", False)  # Default False

        # ------------------ Frames ------------------
        self.f1_toolbar = ttk.Frame(self.root)
        self.f1_toolbar.pack(side="top", fill="x", expand=False)

        self.f2_textBox = ttk.Frame(self.root)
        self.f2_textBox.pack(side="top", fill="both", expand=True)

        self.f3_toolbar = ttk.Frame(self.root)
        self.f3_toolbar.pack(side="top", fill="x", expand=False)

        self.f4_statusbar = ttk.Frame(self.root)
        self.f4_statusbar.pack(side="bottom", fill="x", expand=False)

        # ------------------ Elements ------------------
        # -- f1_toolbar
        # mode
        self.lbl_mode = ttk.Label(self.f1_toolbar, text="Mode:")
        self.lbl_mode.pack(side="left", fill="x", padx=5, pady=5, expand=False)

        self.cb_mode = ttk.Combobox(self.f1_toolbar, values=["Transcribe", "Translate", "Transcribe & Translate"], state="readonly")
        self.cb_mode.pack(side="left", fill="x", padx=5, pady=5, expand=False)
        self.cb_mode.bind("<<ComboboxSelected>>", self.cb_mode_change)

        # model
        self.lbl_model = ttk.Label(self.f1_toolbar, text="Model:")
        self.lbl_model.pack(side="left", fill="x", padx=5, pady=5, expand=False)

        self.cb_model = ttk.Combobox(self.f1_toolbar, values=modelKeys, state="readonly")
        self.cb_model.pack(side="left", fill="x", padx=5, pady=5, expand=False)
        CreateToolTip(
            self.cb_model,
            """Model size, larger models are more accurate but slower and require more VRAM/CPU power. 
            \rIf you have a low end GPU, use Tiny or Base. Don't use large unless you really need it or have super computer because it's very slow.
            \rModel specs: \n- Tiny: ~1 GB Vram\n- Base: ~1 GB Vram\n- Small: ~2 GB Vram\n- Medium: ~5 GB Vram\n- Large: ~10 GB Vram""".strip(),
            wrapLength=400,
        )
        self.cb_model.bind("<<ComboboxSelected>>", lambda _: fJson.savePartialSetting("model", modelSelectDict[self.cb_model.get()]))

        # engine
        self.lbl_engine = ttk.Label(self.f1_toolbar, text="TL Engine:")
        self.lbl_engine.pack(side="left", fill="x", padx=5, pady=5, expand=False)

        self.cb_engine = ttk.Combobox(self.f1_toolbar, values=["Whisper", "Google", "LibreTranslate", "MyMemoryTranslator"], state="readonly")
        self.cb_engine.pack(side="left", fill="x", padx=5, pady=5, expand=False)
        self.cb_engine.bind("<<ComboboxSelected>>", self.cb_engine_change)

        # from
        self.lbl_source = ttk.Label(self.f1_toolbar, text="From:")
        self.lbl_source.pack(side="left", padx=5, pady=5)

        self.cb_sourceLang = ttk.Combobox(self.f1_toolbar, values=engine_select_source_dict["Whisper"], state="readonly")  # initial value
        self.cb_sourceLang.pack(side="left", padx=5, pady=5)
        self.cb_sourceLang.bind("<<ComboboxSelected>>", lambda _: fJson.savePartialSetting("sourceLang", self.cb_sourceLang.get()))

        # to
        self.lbl_to = ttk.Label(self.f1_toolbar, text="To:")
        self.lbl_to.pack(side="left", padx=5, pady=5)

        self.cb_targetLang = ttk.Combobox(self.f1_toolbar, values=[upFirstCase(x) for x in whisper_compatible], state="readonly")  # initial value
        self.cb_targetLang.pack(side="left", padx=5, pady=5)
        self.cb_targetLang.bind("<<ComboboxSelected>>", lambda _: fJson.savePartialSetting("targetLang", self.cb_targetLang.get()))

        # swap
        self.btn_swap = ttk.Button(self.f1_toolbar, text="Swap", command=self.cb_swap_lang)
        self.btn_swap.pack(side="left", padx=5, pady=5)

        # clear
        self.btn_clear = ttk.Button(self.f1_toolbar, text="Clear", command=self.tb_clear)
        self.btn_clear.pack(side="left", padx=5, pady=5)

        # -- f2_textBox
        self.tb_transcribed_bg = tk.Frame(self.f2_textBox, bg="#7E7E7E")
        self.tb_transcribed_bg.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        self.sb_transcribed = tk.Scrollbar(self.tb_transcribed_bg)
        self.sb_transcribed.pack(side="right", fill="y")

        self.tb_transcribed = tk.Text(self.tb_transcribed_bg, height=5, width=25, relief="flat")  # font=("Segoe UI", 10), yscrollcommand=True, relief="flat"
        self.tb_transcribed.bind("<Key>", self.tb_allowed_key)
        self.tb_transcribed.pack(side="left", fill="both", expand=True, padx=1, pady=1)
        self.tb_transcribed.config(yscrollcommand=self.sb_transcribed.set)
        self.sb_transcribed.config(command=self.tb_transcribed.yview)

        self.tb_translated_bg = tk.Frame(self.f2_textBox, bg="#7E7E7E")
        self.tb_translated_bg.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        self.sb_translated = tk.Scrollbar(self.tb_translated_bg)
        self.sb_translated.pack(side="right", fill="y")

        self.tb_translated = tk.Text(self.tb_translated_bg, height=5, width=25, relief="flat")
        self.tb_translated.bind("<Key>", self.tb_allowed_key)
        self.tb_translated.pack(fill="both", expand=True, padx=1, pady=1)
        self.tb_translated.config(yscrollcommand=self.sb_translated.set)
        self.sb_translated.config(command=self.tb_translated.yview)

        # -- f3_toolbar
        self.f3_frameLeft = ttk.Frame(self.f3_toolbar)
        self.f3_frameLeft.pack(side="left", fill="x", expand=True)

        self.f3_leftRow1 = ttk.Frame(self.f3_frameLeft)
        self.f3_leftRow1.pack(side="top", fill="x", expand=True)

        self.f3_leftRow2 = ttk.Frame(self.f3_frameLeft)
        self.f3_leftRow2.pack(side="top", fill="x", expand=True)

        self.f3_frameRight = ttk.Frame(self.f3_toolbar)
        self.f3_frameRight.pack(side="right", fill="x", expand=True)

        self.label_microphone = ttk.Label(self.f3_leftRow1, text="Default Microphone:", font="TkDefaultFont 9 bold")
        self.label_microphone.pack(side="left", padx=5, pady=0, ipady=0)

        self.label_microphone_value = ttk.Label(self.f3_leftRow1, text=getInputDevice()["name"])  # type: ignore
        self.label_microphone_value.pack(side="left", ipadx=0, padx=0, pady=0, ipady=0)

        self.label_speaker = ttk.Label(self.f3_leftRow2, text="Default Speaker:", font="TkDefaultFont 9 bold")  # type: ignore
        self.label_speaker.pack(side="left", padx=5, pady=0, ipady=0)

        self.label_speaker_value = ttk.Label(self.f3_leftRow2, text=getOutputDevice()["name"])  # type: ignore
        self.label_speaker_value.pack(side="left", ipadx=0, padx=0, pady=0, ipady=0)

        # self.f3_center_btn = ttk.Frame(self.f3_toolbar) # f3_toolbar
        # self.f3_center_btn.pack(side="bottom")

        self.btn_record_mic = ttk.Button(self.f3_frameRight, text="Record Mic", command=self.rec_from_mic)
        self.btn_record_mic.pack(side="right", padx=5, pady=5)
        CreateToolTip(self.btn_record_mic, "Record using your default microphone")

        self.btn_record_pc = ttk.Button(self.f3_frameRight, text="Record PC Sound", command=self.rec_from_pc)
        self.btn_record_pc.pack(side="right", padx=5, pady=5)
        CreateToolTip(self.btn_record_pc, "Record sound from your PC ")

        self.btn_record_file = ttk.Button(self.f3_frameRight, text="Record from file")
        self.btn_record_file.pack(side="right", padx=5, pady=5)
        CreateToolTip(self.btn_record_file, "Record from a file (video or audio)")

        # -- f4_statusbar
        # load bar
        self.loadBar = ttk.Progressbar(self.f4_statusbar, orient="horizontal", length=200, mode="determinate")
        self.loadBar.pack(side="left", padx=5, pady=5, fill="x", expand=True)

        # ------------------ Menubar ------------------
        self.menubar = tk.Menu(self.root)
        self.fm_file = tk.Menu(self.menubar, tearoff=0)
        self.fm_file.add_checkbutton(label="Stay on top", command=self.toggle_always_on_top)
        self.fm_file.add_separator()
        self.fm_file.add_command(label="Hide", command=lambda: self.root.withdraw())
        self.fm_file.add_command(label="Exit", command=self.quit_app)
        self.menubar.add_cascade(label="File", menu=self.fm_file)

        self.fm_view = tk.Menu(self.menubar, tearoff=0)
        # self.fm_view.add_command(label="Settings", command=self.open_settings)
        if platform.system() == "Windows":
            self.fm_view.add_checkbutton(label="Log", command=self.toggle_log)
        self.menubar.add_cascade(label="View", menu=self.fm_view)

        self.fm_help = tk.Menu(self.menubar, tearoff=0)
        self.fm_help.add_command(label="About", command=self.open_about)  # placeholder for now
        self.menubar.add_cascade(label="Help", menu=self.fm_help)

        self.root.config(menu=self.menubar)

        # ------------------ Variables ------------------
        # Flags
        self.logOpened = False
        self.always_on_top = False
        self.notified_hidden = False
        gClass.mw = self  # type: ignore

        # ------------------ Bind keys ------------------
        self.root.bind("<F1>", self.open_about)

        # ------------------ on Start ------------------
        # Start polling
        self.root.after(1000, self.isRunningPoll)
        self.onInit()

        # ------------------ Set Icon ------------------
        try:
            self.root.iconbitmap(app_icon)
        except:
            pass

    # ------------------ Handle window ------------------
    # Quit the app
    def quit_app(self):
        if gClass.tray:
            gClass.tray.icon.stop()
        self.root.destroy()
        try:
            exit()
        except SystemExit:
            pass

    # Show window
    def show_window(self):
        self.root.after(0, self.root.deiconify)

    # Close window
    def on_close(self):
        # Only show notification once
        if not self.notified_hidden:
            notification = Notify()
            notification.title = "Hidden to tray"
            notification.message = "The app is still running in the background."
            notification.application_name = app_name
            try:
                notification.icon = app_icon
            except exceptions.InvalidIconPath:
                pass
            notification.send()
            self.notified_hidden = True

        self.root.withdraw()

    # check if the app is running or not, used to close the app from tray
    def isRunningPoll(self):
        if not gClass.running:
            self.quit_app()

        self.root.after(1000, self.isRunningPoll)

    # Toggle Stay on top
    def toggle_always_on_top(self):
        self.always_on_top = not self.always_on_top
        self.root.wm_attributes("-topmost", self.always_on_top)

    def toggle_log(self):
        if self.logOpened:
            hideConsole(gClass.consoleWindow)
        else:
            showConsole(gClass.consoleWindow)

        self.logOpened = not self.logOpened

    # ------------------ Open External Window ------------------
    def open_about(self, _event=None):
        Mbox("About", "Speech Translate", 0)  # !placeholder for now

    # ------------------ Handler ------------------
    # Disable writing, allow copy
    def tb_allowed_key(self, event):
        key = event.keysym

        # Allow
        if key.lower() in ["left", "right"]:  # Arrow left right
            return
        if 12 == event.state and key == "a":  # Ctrl + a
            return
        if 12 == event.state and key == "c":  # Ctrl + c
            return

        # If not allowed
        return "break"

    # ------------------ Functions ------------------
    # on start
    def onInit(self):
        self.cb_mode.set(fJson.settingCache["mode"])
        self.cb_model.set({v: k for k, v in modelSelectDict.items()}[fJson.settingCache["model"]])
        self.cb_sourceLang.set(fJson.settingCache["sourceLang"])
        self.cb_targetLang.set(fJson.settingCache["targetLang"])
        self.cb_engine.set(fJson.settingCache["tl_engine"])

        # update on start
        self.cb_engine_change()
        self.cb_mode_change()
        self.tb_clear()

    # cb engine change
    def cb_engine_change(self, _event=None):
        # save
        fJson.savePartialSetting("tl_engine", self.cb_engine.get())

        self.cb_lang_update()

    def cb_lang_update(self):
        # update the target cb list
        self.cb_targetLang["values"] = engine_select_target_dict[self.cb_engine.get()]

        # update source only if mode is not transcribe only
        mode = self.cb_mode.get()
        if mode != "Transcribe":
            self.cb_sourceLang["values"] = engine_select_source_dict[self.cb_engine.get()]

        # check if the target lang is not in the new list
        if self.cb_targetLang.get() not in self.cb_targetLang["values"]:
            self.cb_targetLang.current(0)

        # check if the source lang is not in the new list
        if self.cb_sourceLang.get() not in self.cb_sourceLang["values"]:
            self.cb_sourceLang.current(0)

    # clear textboxes
    def tb_clear(self):
        self.tb_transcribed.delete(1.0, tk.END)
        self.tb_translated.delete(1.0, tk.END)

    # Swap textboxes
    def tb_swap_content(self):
        tmp = self.tb_transcribed.get(1.0, tk.END)
        self.tb_transcribed.delete(1.0, tk.END)
        self.tb_transcribed.insert(tk.END, self.tb_translated.get(1.0, tk.END))
        self.tb_translated.delete(1.0, tk.END)
        self.tb_translated.insert(tk.END, tmp)

    # swap select language and textbox
    def cb_swap_lang(self):
        # swap lang
        tmp = self.cb_targetLang.get()
        self.cb_sourceLang.set(self.cb_targetLang.get())
        self.cb_targetLang.set(tmp)

        # save
        fJson.savePartialSetting("sourceLang", self.cb_sourceLang.get())
        fJson.savePartialSetting("targetLang", self.cb_targetLang.get())

        # swap text only if mode is transcribe and translate
        if self.cb_mode.current() == 2:
            self.tb_swap_content()

    # change mode
    def cb_mode_change(self, _event=None):
        # get index of cb mode
        index = self.cb_mode.current()

        if index == 0:  # transcribe only
            self.tb_transcribed_bg.pack(side="left", fill="both", expand=True, padx=5, pady=5)
            self.tb_transcribed.pack(fill="both", expand=True, padx=1, pady=1)

            self.tb_translated_bg.pack_forget()
            self.tb_translated.pack_forget()

            self.cb_sourceLang.config(state="readonly")
            self.cb_targetLang.config(state="disabled")

            # reset source lang selection
            self.cb_sourceLang["values"] = engine_select_source_dict["Whisper"]
        elif index == 1:  # translate only
            self.tb_transcribed_bg.pack_forget()
            self.tb_transcribed.pack_forget()

            self.tb_translated_bg.pack(side="left", fill="both", expand=True, padx=5, pady=5)
            self.tb_translated.pack(fill="both", expand=True, padx=1, pady=1)

            self.cb_sourceLang.config(state="readonly")
            self.cb_targetLang.config(state="readonly")
            self.cb_lang_update()

        elif index == 2:  # transcribe and translate
            self.tb_transcribed_bg.pack(side="left", fill="both", expand=True, padx=5, pady=5)
            self.tb_transcribed.pack(fill="both", expand=True, padx=1, pady=1)

            self.tb_translated_bg.pack(side="left", fill="both", expand=True, padx=5, pady=5)
            self.tb_translated.pack(fill="both", expand=True, padx=1, pady=1)

            self.cb_sourceLang.config(state="readonly")
            self.cb_targetLang.config(state="readonly")
            self.cb_lang_update()

        # save
        fJson.savePartialSetting("mode", self.cb_mode.get())

    def disable_interactions(self):
        self.cb_mode.config(state="disabled")
        self.cb_model.config(state="disabled")
        self.cb_engine.config(state="disabled")
        self.cb_sourceLang.config(state="disabled")
        self.cb_targetLang.config(state="disabled")
        self.btn_swap.config(state="disabled")
        self.btn_record_mic.config(state="disabled")
        self.btn_record_pc.config(state="disabled")
        self.btn_record_file.config(state="disabled")

    def enable_interactions(self):
        self.cb_mode.config(state="readonly")
        self.cb_model.config(state="readonly")
        self.cb_engine.config(state="readonly")
        self.cb_sourceLang.config(state="readonly")
        self.cb_targetLang.config(state="readonly")
        self.btn_swap.config(state="normal")
        self.btn_record_mic.config(state="normal")
        self.btn_record_pc.config(state="normal")
        self.btn_record_file.config(state="normal")

    def start_loadBar(self):
        self.loadBar.config(mode="indeterminate")
        self.loadBar.start()

    def stop_loadBar(self, rec_type: Literal["mic", "pc", "file"]):
        self.loadBar.stop()
        self.loadBar.config(mode="determinate")

        # check first if it's recording or not
        if not gClass.recording:
            return

        if rec_type == "mic":
            self.btn_record_mic.config(text="Stop")
        elif rec_type == "pc":
            self.btn_record_pc.config(text="Stop")
        elif rec_type == "file":
            self.btn_record_file.config(text="Stop")

    # ------------------ Rec ------------------
    # From mic
    def rec_from_mic(self):
        self.tb_clear()

        # get value of cb mode
        mode = self.cb_mode.get()
        model = self.cb_model.get()
        sourceLang = self.cb_sourceLang.get().lower()
        targetLang = self.cb_targetLang.get().lower()
        engine = self.cb_engine.get()
        verbose = fJson.settingCache["verbose"]
        cutOff = fJson.settingCache["cutOff"]

        if sourceLang == targetLang:
            Mbox("Invalid options!", "Source and target language cannot be the same", 2)
            return

        # ui changes
        self.start_loadBar()
        self.disable_interactions()
        self.btn_record_mic.config(text="Loading", command=self.rec_from_mic_stop, state="normal")

        # Record
        gClass.recording = True
        if mode == "Transcribe":
            transcribeThread = threading.Thread(target=rec_mic, args=(model, sourceLang, targetLang, True, False, engine, verbose, cutOff))
            transcribeThread.start()
        elif mode == "Translate":
            translateThread = threading.Thread(target=rec_mic, args=(model, sourceLang, targetLang, False, True, engine, verbose, cutOff))
            translateThread.start()
        elif mode == "Transcribe & Translate":
            transcribeTranslateThread = threading.Thread(target=rec_mic, args=(model, sourceLang, targetLang, True, True, engine, verbose, cutOff))
            transcribeTranslateThread.start()

    def rec_from_mic_stop(self):
        gClass.recording = False
        self.loadBar.stop()
        self.loadBar.config(mode="determinate")
        self.btn_record_mic.config(text="Record From Mic", command=self.rec_from_mic)
        self.enable_interactions()

    def rec_from_pc(self):
        # check if on windows or not
        if platform.system() != "Windows":
            Mbox(
                "Not available",
                """This feature is only available on Windows. 
                \rIn order to record PC sound from OS other than Windows you will need to create a virtual audio loopback to pass the speaker output as an input. You can use software like PulseAudio to do this.
                \rAfter that you can change your default input device to the virtual audio loopback.""",
                0,
                self.root,
            )
            return

        # get value of cb mode
        mode = self.cb_mode.get()
        model = self.cb_model.get()
        sourceLang = self.cb_sourceLang.get().lower()
        targetLang = self.cb_targetLang.get().lower()
        engine = self.cb_engine.get()
        verbose = fJson.settingCache["verbose"]
        cutOff = fJson.settingCache["cutOff"]

        if sourceLang == targetLang:
            Mbox("Invalid options!", "Source and target language cannot be the same", 2)
            return


if __name__ == "__main__":
    if platform.system() == "Windows":
        consoleWindow = win32gui.GetForegroundWindow()
        hideConsole(consoleWindow)
        gClass.consoleWindow = consoleWindow

    main = MainWindow()
    tray = AppTray()  # Start tray app in the background
    main.root.mainloop()  # Start main app
