"""Plugins for extending Zealot functionality"""
from .interface import (
    ZealotPlugin,
    PluginContext,
    PluginResult,
    CommandPlugin,
    PythonPlugin,
    PluginManager
)

__all__ = [
    'ZealotPlugin',
    'PluginContext',
    'PluginResult',
    'CommandPlugin',
    'PythonPlugin',
    'PluginManager'
]
