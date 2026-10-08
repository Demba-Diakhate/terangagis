from __future__ import annotations
import json, threading, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from qgis.PyQt.QtCore import QCoreApplication, QEvent, QObject
from qgis.core import QgsProject, QgsVectorLayer
from plugin.core.errors import TerangaError
