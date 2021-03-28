# -*- coding: utf-8 -*-
"""Main script for executing Pinsect-Cam."""

import argparse
import pathlib
import sys

from pinsect import model
from pinsect import ui


def run(args):
    """Main entry point after parsing the command line arguments."""
    # Load configuration.
    config = model.AppConfig.load(args.config_path)
    # Initialize state and create model.
    state = model.AppState(args, config)
    app_model = model.AppModel(state)
    # Launch application.
    ui.AppFrame.launch(app_model)
    # Update configuration from application state.
    config.interval = app_model.state.interval
    config.work_dir = app_model.state.work_dir
    config.save(args.config_path)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--config-path',
        default=str(pathlib.Path.home() / '.pinsect-cam.json'),
        help='Path to configuration file to read')
    parser.add_argument(
        '--interval', type=float,
        help='Interval (in seconds) between photos')
    parser.add_argument(
        '--work-dir',
        help='The work directory of the app')
    parser.add_argument(
        '--min-free', type=int,
        help='Minimal free storage in target directory in MB')
    args = parser.parse_args(argv)
    return run(args)


if __name__ == '__main__':
    sys.exit(main())