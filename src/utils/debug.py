"""
Debug Mode for QuestCut-AI
=======================
Conditional logging and performance timing.
"""
import os
import logging
import time
import functools
from typing import Optional, Callable, Any
from contextlib import contextmanager
from dataclasses import dataclass, field

DEBUG = os.environ.get('MADPEEL_DEBUG', '').lower() in ('1', 'true', 'yes')
TRACK_PERFORMANCE = DEBUG or os.environ.get('MADPEEL_PERF', '').lower() in ('1', 'true', 'yes')


@dataclass
class PerformanceMetric:
    name: str = ''
    duration: float = 0.0
    metadata: dict = field(default_factory=dict)


class PerformanceTracker:
    """Tracks performance metrics for optimization."""

    def __init__(self, enabled=None):
        self.enabled = enabled if enabled is not None else TRACK_PERFORMANCE
        self.metrics = []
        self._logger = logging.getLogger('performance')

    @contextmanager
    def measure(self, name=None, **metadata):
        """Context manager for measuring duration."""
        if not self.enabled:
            yield
            return
        start = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start
            metric = PerformanceMetric(name=name, duration=duration, metadata=metadata)
            self.metrics.append(metric)
            self._logger.debug(f'{name}: {duration * 1000:.2f}ms')

    def track(self, name=None):
        """Decorator for tracking function performance."""

        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if not self.enabled:
                    return func(*args, **kwargs)
                start = time.perf_counter()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = time.perf_counter() - start
                    metric = PerformanceMetric(name=name or func.__name__, duration=duration)
                    self.metrics.append(metric)

            return wrapper

        return decorator

    def get_metrics(self, name=None):
        """Get metrics, optionally filtered by name."""
        if name:
            return [m for m in self.metrics if m.name == name]
        return self.metrics.copy()

    def get_average(self, name=None):
        """Get average duration for a named operation."""
        metrics = self.get_metrics(name)
        if not metrics:
            return None
        return sum(m.duration for m in metrics) / len(metrics)

    def get_summary(self):
        """Get summary of all metrics."""
        summary = {}
        names = {m.name for m in self.metrics}
        for name in names:
            metrics = self.get_metrics(name)
            durations = [m.duration for m in metrics]
            summary[name] = {
                'count': len(metrics),
                'total': sum(durations),
                'average': sum(durations) / len(durations),
                'min': min(durations),
                'max': max(durations),
            }
        return summary

    def clear(self):
        """Clear all metrics."""
        self.metrics.clear()

    def print_summary(self):
        """Print a formatted summary."""
        summary = self.get_summary()
        print('\n' + '=' * 60)
        print('Performance Summary')
        print('=' * 60)
        for name, stats in sorted(summary.items(), key=lambda x: -x[1]['total']):
            print(f'\n{name}:')
            print(f"  Count:   {stats['count']}")
            print(f"  Total:   {stats['total'] * 1000:.2f}ms")
            print(f"  Average: {stats['average'] * 1000:.2f}ms")
            print(f"  Min:     {stats['min'] * 1000:.2f}ms")
            print(f"  Max:     {stats['max'] * 1000:.2f}ms")
        print('\n' + '=' * 60)


class DebugLogger:
    """Debug logger that only logs when DEBUG is enabled."""

    def __init__(self, name=None):
        self._logger = logging.getLogger(name)
        self.enabled = DEBUG

    def log(self, message=None, **kwargs):
        """Log a debug message."""
        if not self.enabled:
            return
        if kwargs:
            extras = ', '.join(f'{k}={v}' for k, v in kwargs.items())
            message = f'{message} [{extras}]'
        self._logger.debug(message)

    def info(self, message=None, **kwargs):
        """Log info (always logged)."""
        if kwargs:
            extras = ', '.join(f'{k}={v}' for k, v in kwargs.items())
            message = f'{message} [{extras}]'
        self._logger.info(message)

    def warning(self, message=None, **kwargs):
        """Log warning (always logged)."""
        if kwargs:
            extras = ', '.join(f'{k}={v}' for k, v in kwargs.items())
            message = f'{message} [{extras}]'
        self._logger.warning(message)

    def error(self, message=None, **kwargs):
        """Log error (always logged)."""
        if kwargs:
            extras = ', '.join(f'{k}={v}' for k, v in kwargs.items())
            message = f'{message} [{extras}]'
        self._logger.error(message)


def setup_debug_logging():
    """Setup logging configuration for debug mode."""
    level = logging.DEBUG if DEBUG else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S',
    )
    perf_logger = logging.getLogger('performance')
    perf_logger.setLevel(logging.DEBUG if TRACK_PERFORMANCE else logging.WARNING)
    if DEBUG:
        logging.info('Debug mode enabled')
    if TRACK_PERFORMANCE:
        logging.info('Performance tracking enabled')


def debug_only(func=None):
    """Decorator that only executes function in debug mode."""

    def wrapper(*args, **kwargs):
        if DEBUG:
            return func(*args, **kwargs)

    return wrapper


_tracker: Optional[PerformanceTracker] = None


def get_tracker():
    """Get the global performance tracker."""
    global _tracker
    if _tracker is None:
        _tracker = PerformanceTracker()
    return _tracker


@contextmanager
def measure(name=None, **metadata):
    """Measure duration of a code block."""
    with get_tracker().measure(name, **metadata) as _:
        yield


def track(name=None):
    """Track performance of a function."""
    return get_tracker().track(name)
