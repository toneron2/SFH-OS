"""Manifest module - Communication protocol between agents."""

from .request import RequestManifest
from .constraint import ConstraintManifest
from .result import ResultManifest

__all__ = ["RequestManifest", "ConstraintManifest", "ResultManifest"]
