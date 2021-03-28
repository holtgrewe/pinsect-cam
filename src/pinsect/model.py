# -*- coding: utf-8 -*-
"""Model / state of the Pinsect-Cam application."""

import datetime
import json
import pathlib
import shutil
import subprocess
import sys
import time
import threading
from tkinter import messagebox

from . import ui

#: State is idle.
IDLE = 'idle'

#: State is recording.
RECORDING = 'recording'

#: State is preview.
PREVIEW = 'preview'

#: List of available states.
STATES = (
    IDLE,
    RECORDING,
    PREVIEW
)

#: Default configuration.
DEFAULT_CONFIG_ = (
    # Interval between two recordings.
    ('interval', 60),
    # Work directory.
    ('work_dir', str(pathlib.Path.home() / 'pinsect-cam')),
    # Minimal free space.
    ('min_free', 50)
)
DEFAULT_CONFIG = dict(DEFAULT_CONFIG_)

#: Smallest possible interval
MIN_INTERVAL = 1
#: Largest possible interval (10 min)
MAX_INTERVAL = 60 * 10


class AppConfig:
    """Configuration of the application."""

    def __init__(
            self,
            interval=DEFAULT_CONFIG['interval'],
            work_dir=DEFAULT_CONFIG['work_dir'],
            min_free=DEFAULT_CONFIG['min_free'],
            **kwargs):
        #: The interval (in seconds) between two configurations.
        self.interval = interval
        #: The working directory.
        self.work_dir = work_dir
        #: Minimum amount of free space in MB.
        self.min_free = min_free
    
    @classmethod
    def load(klass, path):
        """Load configuration from ``path``."""
        try:
            with open(path, 'rt') as inputf:
                print('Loading config from {}'.format(path), file=sys.stderr)
                return AppConfig(**json.load(inputf))
        except OSError as _e:
            return AppConfig()

    def save(self, path):
        """Save configuration to ``path``."""
        with open(path, 'wt') as outputf:
            print('Saving config to {}'.format(path), file=sys.stderr)
            json.dump(vars(self), outputf)


class AppState:
    """State of the configuration."""

    def __init__(self, args, config):
        self.state = IDLE
        self.interval = args.interval or config.interval
        self.work_dir = args.work_dir or config.work_dir
        self.min_free = args.min_free or config.min_free
        self.on_image = lambda path: None
        self.on_uiupdate = lambda: None


class AppModel:
    """The main model of the application."""

    def __init__(self, state):
        #: The application's state.
        self.state = state

    def start_preview(self):
        """Start camera preview (one image every second).

        Return path to temporary preview image.
        """
        print('Starting preview to {}...'.format(self.preview_path()),
              file=sys.stderr)
        self.state.state = PREVIEW
        thread = PreviewThread(self.state, self)
        res = thread.get_jpeg_path()
        thread.start()
        self.state.on_uiupdate()
        return res

    def preview_path(self):
        return pathlib.Path(self.state.work_dir) / 'preview.jpeg'

    def stop_preview(self):
        """Stop preview."""
        if self.state.state != PREVIEW:
            return
        print('Stopping preview.', file=sys.stderr)
        self.state.state = IDLE
        self.state.on_uiupdate()

    def start_recording(self):
        print('Starting recording to {}...'.format(self.state.work_dir),
              file=sys.stderr)
        self.state.state = RECORDING
        thread = RecordThread(self.state, self)
        res = thread.get_jpeg_path()
        thread.start()
        self.state.on_uiupdate()
        return res

    def stop_recording(self):
        print('Stopping recording.', file=sys.stderr)
        self.state.state = IDLE
        self.state.on_uiupdate()

    def get_interval(self):
        return self.state.interval

    def set_interval(self, interval):
        print('Setting interval to: {}'.format(interval), file=sys.stderr)
        if interval < MIN_INTERVAL or interval > MAX_INTERVAL:
            return  # guard; short-circuit
        self.state.interval = interval


class RaspiStillThread:
    """Base class for thread writing images to files via ``raspistill``."""

    def __init__(self, app_state, model):
        self.app_state = app_state
        self.model = model
        self.running = False
        self.stop = False
        self.lock = threading.RLock()
    
    def get_interval(self):
        """Return seconds to sleep."""
        raise NotImplementedError('Implement me!')

    def get_jpeg_path(self):
        """Return path to JPEG."""
        raise NotImplementedError('Implement me!')

    def _run(self):
        """Execute thread, to not call manually."""
        with self.lock:
            self.running = True
            self.stop = False
        while not self.stop:
            if self._should_stop_full():
                break
            else:
                self.take_image()
                time.sleep(self.get_interval())
        with self.lock:
            self.stop = False
            self.running = False

    def _should_stop_full(self):
        """Check whether we should stop because of low space."""
        free_bytes = shutil.disk_usage(str(pathlib.Path(path).parent)).free
        if free_bytes < self.app_state.min_free * 1024 * 1024:
            self.stop = True
            messagebox.showerror(
                title="Disk full",
                message="Stop recording because disk is full",
            )
            return True
        else:
            return False

    def take_image(self):
        QUALITY = '90'
        path = self.get_jpeg_path()
        try:
            path = self.get_jpeg_path()
            pathlib.Path(path).parent.mkdir(
                    exist_ok=True, parents=True)
            print('Taking image to {}...'.format(path), file=sys.stderr)
            subprocess.run([
                'raspistill',
                '-q', QUALITY,
                '-o', path,
                '-vf',
                '-hf',
            ])
            time.sleep(0.5)
            print('on_image = {}'.format(self.app_state.on_image), file=sys.stderr)
            self.app_state.on_image(path)
            print(' => done', file=sys.stderr)
        except Exception as e:
            print('ERROR: {}'.format(e), file=sys.stderr)
            ui.show_error('ERROR: {}'.format(e))
            self.model.stop_preview()
            self.model.stop_recording()
            self.stop()
            raise

    def start(self):
        """Start thread."""
        with self.lock:
            if self.running:
                print('Cannot start twice!', file=sys.stderr)
            else:
                thread = threading.Thread(target=self._run, args=())
                thread.daemon = True
                thread.start()

    def stop(self):
        """Stop thread."""
        with self.lock:
            if not self.running:
                print('Not started; cannot stop', file=sys.stderr)
                return
            self.stop = True


class PreviewThread(RaspiStillThread):
    def get_interval(self):
        return 1

    def get_jpeg_path(self):
        return str(pathlib.Path(self.app_state.work_dir) / 'preview.jpeg')


class RecordThread(RaspiStillThread):
    def get_interval(self):
        return self.app_state.interval

    def get_jpeg_path(self):
        now = datetime.datetime.now()
        token = now.strftime('%Y-%m-%d_%H-%M-%S')
        path = pathlib.Path(self.app_state.work_dir) / str(now.year)
        path.mkdir(exist_ok=True, parents=True)
        return str(path / 'MBF_{}.jpeg'.format(token))

