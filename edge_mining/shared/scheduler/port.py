"""Scheduler Port"""

from abc import ABC, abstractmethod

class SchedulerPort(ABC):
    """Port for the Scheduler."""
    @abstractmethod
    def start(self):
        """Starts the scheduler"""
        raise NotImplementedError

    @abstractmethod
    def stop(self):
        """Stops the scheduler"""
        raise NotImplementedError
