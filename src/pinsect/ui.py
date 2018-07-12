# -*- coding: utf-8 -*-

import pathlib

import tkinter as tk
from tkinter import messagebox
from PIL import ImageTk, Image
import sys

from . import model


def show_error(msg):
    messagebox.showerror('ERROR', msg)


class _ComponentBuilder:
    """Helper class for building UI components."""
    def __init__(self, model, master, frame):
        self.model = model
        self.master = master
        self.frame = frame

    def run(self):
        """Build components and return ``dict`` with the UI widgets."""
        self.master.geometry('400x400')
        self.master.rowconfigure(0, weight=10)
        self.master.rowconfigure(1, weight=1)
        self.master.columnconfigure(3, weight=1)
        result = {
            'interval_var': tk.StringVar(),
            'original': Image.open(
                str(pathlib.Path(__file__).parent / 'default.jpg')),
            'image': None,
        }
        result.update({
            'image_display': tk.Canvas(
                self.master, width=100, height=100, background='bisque'),
            'preview_button': tk.Button(
                self.master, text='Preview', command=self.frame.preview_clicked),
            'record_button': tk.Button(
                self.master, text='Record', command=self.frame.record_clicked),
            'interval_entry': tk.Entry(
                self.master, textvariable=result['interval_var'], width=6,
                justify=tk.RIGHT),
            'interval_label': tk.Label(self.master, text='[s]'),
            'interval_inc_button': tk.Button(
                self.master, text='+', command=self.frame.interval_inc_clicked),
            'interval_dec_button': tk.Button(
                self.master, text='-', command=self.frame.interval_dec_clicked),
        })
        result['image_display'].grid(
            row=0, column=0,
            columnspan=6, sticky=(tk.W + tk.E + tk.N + tk.S),
            padx=2, pady=2)
        result['interval_var'].set(str(self.model.state.interval))
        result['interval_var'].trace('w', self.frame.interval_changed)
        result['preview_button'].grid(
            row=1, column=0,
            sticky=(tk.W + tk.S),
        )
        result['interval_entry'].grid(
            row=1, column=1,
            sticky=(tk.W + tk.S + tk.E),
        )
        result['interval_label'].grid(
            row=1, column=2,
            sticky=(tk.E + tk.S),
        )
        result['interval_inc_button'].grid(
            row=1, column=3,
            sticky=(tk.S + tk.E),
        )
        result['interval_dec_button'].grid(
            row=1, column=4,
            sticky=(tk.S + tk.E),
        )
        result['record_button'].grid(
            row=1, column=5,
            sticky=(tk.S + tk.E),
        )
        return result


class AppFrame(tk.Frame):
    """The main frame of the application."""

    @staticmethod
    def launch(app_model):
        """Launch UI with frame."""
        root = tk.Tk()
        main_frame = AppFrame(master=root, model=app_model)
        return main_frame.mainloop()

    def __init__(self, master, model, **kwargs):
        super().__init__(master, **kwargs)
        self.master.wm_title('PInsect-Cam')
        #: The ``AppModel`` to use for the application.
        self.model = model
        #: A dict mapping names to UI components.
        self.components = _ComponentBuilder(model, master, self).run()
        #: Render and resize the image.
        self.image_loaded()
        self.master.bind('<Configure>', self.on_resize)
        self.model.state.on_image = self.image_changed
        self.model.state.on_uiupdate = self.on_resize

    def image_loaded(self):
        print('Updating image...', file=sys.stderr)
        self.state_updated()
        orig_width, orig_height = self.components['original'].size
        scale_width = (
            self.components['image_display'].winfo_width() / orig_width)
        scale_height = (
            self.components['image_display'].winfo_height() / orig_height)
        scale = min(scale_width, scale_height)
        new_width = max(int(orig_width * scale), 1)
        new_height = max(int(orig_height * scale), 1)
        # print(orig_width, orig_height, self.components['image_display'].winfo_width(),
        #       self.components['image_display'].winfo_height(), scale, new_width, new_height)
        self.components['resized'] = self.components['original'].resize(
                (new_width, new_height), Image.BILINEAR)
        self.components['photo'] = ImageTk.PhotoImage(self.components['resized'])
        self.components['image_display'].create_image(
            (0, 0), anchor=tk.NW, image=self.components['photo'],
            tags='all')

    def on_resize(self, _event=None):
        self.state_updated()
        self.image_loaded()

    def state_updated(self):
        """Internal state updated; also update state of UI widgets."""
        if self.model.state.state == model.IDLE:
            for x in (
                    'preview_button', 'record_button', 'interval_entry',
                    'interval_label', 'interval_inc_button',
                    'interval_dec_button'):
                self.components[x]['state'] = tk.NORMAL
            self.components['preview_button']['text'] = 'Preview'
            self.components['record_button']['text'] = 'Record'
        elif self.model.state.state == model.PREVIEW:
            for x in (
                    'record_button', 'interval_entry',
                    'interval_label', 'interval_inc_button',
                    'interval_dec_button'):
                self.components[x]['state'] = tk.DISABLED
            self.components['preview_button']['state'] = tk.NORMAL
            self.components['preview_button']['text'] = '[Previewing]'
            self.components['record_button']['text'] = 'Record'
        elif self.model.state.state == model.RECORDING:
            for x in (
                    'preview_button', 'interval_entry',
                    'interval_label', 'interval_inc_button',
                    'interval_dec_button'):
                self.components[x]['state'] = tk.DISABLED
            self.components['record_button']['state'] = tk.NORMAL
            self.components['preview_button']['text'] = 'Preview'
            self.components['record_button']['text'] = '[Recording]'

    def preview_clicked(self):
        """Preview button was clicked."""
        if self.model.state.state == model.PREVIEW:
            self.model.stop_preview()
        else:
            self.model.start_preview()
        self.state_updated()

    def record_clicked(self):
        """Record button was clicked."""
        if self.model.state.state == model.RECORDING:
            self.model.stop_recording()
        else:
            self.model.start_recording()
        self.state_updated()

    def image_changed(self, path):
        print('Image changed...', file=sys.stderr)
        self.components['original'] = Image.open(path)
        self.image_loaded()

    def interval_changed(self, *args):
        """Update the record interval."""
        try:
            interval = int(self.components['interval_var'].get())
        except ValueError:
            return
        if interval < model.MIN_INTERVAL:
            interval = model.MIN_INTERVAL
        elif interval > model.MAX_INTERVAL:
            interval = model.MAX_INTERVAL
        widget_interval = interval  # XXX
        self.model.set_interval(interval)
        self.state_updated()

    def interval_dec_clicked(self):
        """Clicked on interval decrement button."""
        if self.model.get_interval() > model.MIN_INTERVAL:
            self.model.set_interval(self.model.get_interval() - 1)
            self.state_updated()
            self.components['interval_var'].set(str(self.model.get_interval()))

    def interval_inc_clicked(self):
        """Clicked on interval increment button."""
        if self.model.get_interval() < model.MAX_INTERVAL:
            self.model.set_interval(self.model.get_interval() + 1)
            self.state_updated()
            self.components['interval_var'].set(str(self.model.get_interval()))
