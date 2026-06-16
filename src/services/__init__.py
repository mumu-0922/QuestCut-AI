"""Reusable service layer shared by desktop, web, and Docker entrypoints."""

from .cutout_service import CutoutResult, CutoutService, get_cutout_service

__all__ = ["CutoutResult", "CutoutService", "get_cutout_service"]
