#!/usr/bin/env python3
"""Decides whether an inbox note is finished and old enough to archive."""
import os
import time


def _age_days(path):
    try:
        return (time.time() - os.path.getmtime(path)) / 86400.0
    except OSError:
        return 0.0


def _looks_done(path):
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read().lower()
    except OSError:
        return False
    if "#todo" in text or "- [ ]" in text:
        return False
    return True


def is_finished(path, min_age_days):
    if _age_days(path) < min_age_days:
        return False
    return _looks_done(path)
