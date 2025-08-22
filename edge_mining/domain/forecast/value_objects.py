"""Collection of Value Objects for the Energy Forecast domain of the Edge Mining application."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional

from edge_mining.domain.common import Timestamp, ValueObject, WattHours, Watts


@dataclass(frozen=True)
class Sun(ValueObject):
    """Value Object for sunrise and sunset times."""

    # The time in the morning when the sun is a specific number of degrees
    # below the horizon.
    dawn: datetime
    # The time in the morning when the top of the sun breaks the horizon.
    sunrise: datetime
    # The time when the sun is at its highest point directly above the observer.
    noon: datetime
    # The time when the sun is at its lowest point.
    midnight: datetime
    # The time in the evening when the sun is about to disappear below the horizon.
    sunset: datetime
    # The time in the evening when the sun is a specific number of degrees
    # below the horizon.
    dusk: datetime
    # The time when the sun is up i.e. between sunrise and sunset.
    daylight: timedelta
    # The time between astronomical dusk of one day and astronomical dawn of the next.
    night: timedelta
    # The time between dawn and sunrise or between sunset and dusk.
    twilight: timedelta

    # The number of degrees clockwise from North at which the sun can be seen.
    azimuth: Optional[float] = field(default=None)
    # The angle of the sun down from directly above the observer.
    zenith: Optional[float] = field(default=None)
    # The number of degrees up from the horizon at which the sun can be seen.
    elevation: Optional[float] = field(default=None)

    @property
    def time_before_sunrise(self) -> Optional[timedelta]:
        """Returns the time remaining until sunrise."""
        if self.sunrise < datetime.now():
            return None
        return self.sunrise - datetime.now()

    @property
    def time_after_sunrise(self) -> Optional[timedelta]:
        """Returns the time elapsed since sunrise."""
        return datetime.now() - self.sunrise

    @property
    def time_before_sunset(self) -> Optional[timedelta]:
        """Returns the time remaining until sunset."""
        if self.sunset < datetime.now():
            return None
        return self.sunset - datetime.now()

    @property
    def time_after_sunset(self) -> Optional[timedelta]:
        """Returns the time elapsed since sunset."""
        return datetime.now() - self.sunset


@dataclass(frozen=True)
class ForecastPowerPoint(ValueObject):
    """Value Object for a single forecast power point."""

    timestamp: Timestamp
    power: Watts


@dataclass(frozen=True)
class ForecastInterval(ValueObject):
    """Value Object for a forecast energy interval."""

    start: Timestamp
    end: Timestamp
    energy: Optional[WattHours] = None
    energy_remaining: Optional[WattHours] = None
    power_points: List[ForecastPowerPoint] = field(default_factory=list)

    @property
    def duration(self) -> timedelta:
        """Calculate the duration of the interval"""
        return self.end - self.start

    @property
    def avg_power(self) -> Watts:
        """Calculate the average power over the interval."""
        if not self.power_points:
            return Watts(0.0)

        total_power = sum(point.power for point in self.power_points)
        return Watts(total_power / len(self.power_points)) if total_power else Watts(0.0)
