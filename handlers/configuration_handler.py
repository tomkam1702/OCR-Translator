from PySide6.QtCore import QTimer
# handlers/configuration_handler.py
import os
import re # Not used directly here, but ui_interaction_handler uses it
import sys
from logger import log_debug
from resource_handler import get_resource_path


class ConfigurationHandler:
    def __init__(self, app):
        self.app = app



