# -*- coding: utf-8 -*-
"""Model / state of the Pinsect-Cam application."""

import json
import pathlib
import sys

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
    ('interval', 5),
    # Work directory.
    ('work_dir', str(pathlib.Path.home() / 'pinsect-cam')),
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
            **kwargs):
        #: The interval (in seconds) between two configurations.
        self.interval = interval
        #: The working directory.
        self.work_dir = work_dir
    
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
        return self.preview_path()

    def preview_path(self):
        return pathlib.Path(self.state.work_dir) / 'preview.jpeg'

    def stop_preview(self):
        """Stop preview."""
        if self.state.state != PREVIEW:
            return
        print('Stopping preview.', file=sys.stderr)
        self.state.state = IDLE

    def start_recording(self):
        print('Starting recording to {}...'.format(self.state.work_dir),
              file=sys.stderr)
        self.state.state = RECORDING

    def stop_recording(self):
        print('Stopping recording.', file=sys.stderr)
        self.state.state = IDLE

    def get_interval(self):
        return self.state.interval

    def set_interval(self, interval):
        print('Setting interval to: {}'.format(interval), file=sys.stderr)
        if interval < MIN_INTERVAL or interval > MAX_INTERVAL:
            return  # guard; short-circuit
        self.state.interval = interval
