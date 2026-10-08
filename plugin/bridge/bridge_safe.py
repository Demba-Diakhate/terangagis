from __future__ import annotations
import json, threading, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from qgis.PyQt.QtCore import QCoreApplication, QObject, QMetaObject, Qt
from qgis.core import QgsProject, QgsVectorLayer
from plugin.core.errors import TerangaError

class BridgeError(TerangaError): pass

class _Invoker(QObject):
    def __init__(self): super().__init__(); self._res=None; self._err=None; self._done=threading.Event()
    def _exec(self, fn): 
        try: self._res=fn()
        except Exception as e: self._err=e
        self._done.set()
    def invoke(self, fn):
        self._res=self._err=None; self._done.clear()
        QMetaObject.invokeMethod(self, '_exec', Qt.QueuedConnection, fn)
        if not self._done.wait(30): raise RuntimeError('timeout')
        if self._err: raise self._err
        return self._res
