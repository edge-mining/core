""" "Collection of Aggregate Roots for the Forecast domain of the Edge Mining application."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional

from edge_mining.domain.common import AggregateRoot, Timestamp, WattHours, Watts
from edge_mining.domain.forecast.value_objects import ForecastInterval


@dataclass
class Forecast(AggregateRoot):
    """Aggregate Root for the Forecast domain."""

    timestamp: Timestamp = field(default_factory=Timestamp(datetime.now()))
    intervals: List[ForecastInterval] = field(default_factory=list)

    @property
    def next_hour_power(self) -> Optional[Watts]:
        """Get the forecasted power for the next hour."""
        if not self.intervals:
            return None

        # Sort intervals by start time
        self.sort_intervals()

        # Find the first interval that starts in the next hour
        next_hour_start = datetime.now() + timedelta(hours=1)

        for interval in self.intervals:
            if interval.start <= next_hour_start < interval.end:
                # Get the average power in this interval
                if interval.power_points:
                    return interval.avg_power

        return None

    @property
    def avg_next_4_hours_power(self) -> Watts:
        """Get the average predicted power for the next 4 hours."""
        if not self.intervals:
            return Watts(0.0)

        # Sort intervals by start time
        self.sort_intervals()

        total_power = 0.0
        count = 0

        # Calculate average power over the next 4 hours
        now = datetime.now()
        four_hours_later = now + timedelta(hours=4)

        for interval in self.intervals:
            if interval.start < four_hours_later and interval.end > now:
                total_power += interval.avg_power
                count += 1

        if count == 0:
            return Watts(0.0)

        avg_power = total_power / count
        return Watts(round(avg_power, 3))

    @property
    def next_hour_energy(self) -> WattHours:
        """Get the predicted energy for the next hour."""
        if not self.intervals:
            return WattHours(0.0)

        # Sort intervals by start time
        self.sort_intervals()

        total_energy = WattHours(0.0)

        # Calculate energy for the next hour
        now = datetime.now()
        next_hour_start = now + timedelta(hours=1)
        next_hour_end = next_hour_start + timedelta(hours=1)

        for interval in self.intervals:
            if interval.start < next_hour_end and interval.end > next_hour_start:
                # Calculate overlap window
                overlap_start = max(interval.start, next_hour_start)
                overlap_end = min(interval.end, next_hour_end)
                if overlap_start < overlap_end:
                    # Calculate energy for the overlapping interval
                    overlap_duration_sec = (overlap_end - overlap_start).total_seconds()
                    interval_duration_sec = interval.duration.total_seconds()

                    if interval_duration_sec > 0:
                        # Compute the energy ratio for the overlapping interval
                        ratio = overlap_duration_sec / interval_duration_sec
                        if interval.energy is not None:
                            # Ensure energy is not None before multiplying
                            total_energy = WattHours(total_energy + float(interval.energy) * ratio)

        return WattHours(round(total_energy, 3)) if total_energy > 0 else WattHours(0.0)

    def sort_intervals(self) -> None:
        """Sort intervals and power points within them."""
        self.intervals.sort(key=lambda i: i.start)
        for interval in self.intervals:
            interval.power_points.sort(key=lambda p: p.timestamp)

    def get_power_at_time(self, time: datetime) -> Optional[Watts]:
        """
        Get the forecasted power at a specific time, using linear interpolation if necessary.
        """
        self.sort_intervals()  # Ensure intervals are sorted

        total_points = [p for i in self.intervals for p in i.power_points]
        if not total_points:
            return None

        # Find the interval that contains the time
        point_first = None
        point_last = None

        for point in total_points:
            if point.timestamp == time:
                return point.power  # Exact match
            if point.timestamp < time:
                point_first = point
            elif point.timestamp > time:
                point_last = point
                break  # If we found a point after the time, we can stop

        # If we don't have both points, we can't interpolate
        if point_first is None or point_last is None:
            return None

        # Linear interpolation
        time_diff = (point_last.timestamp - point_first.timestamp).total_seconds()
        time_diff_target = (time - point_first.timestamp).total_seconds()
        if time_diff == 0:
            return point_first.power
        ratio = time_diff_target / time_diff
        interpolated_power = point_first.power + (point_last.power - point_first.power) * ratio
        interpolated_power = round(interpolated_power, 3)  # Round to 3 decimal places
        return Watts(interpolated_power)

    def get_energy_over_interval(self, start: Timestamp, end: Timestamp) -> Optional[WattHours]:
        """Get the total energy forecasted over a specific time interval."""
        total_energy = WattHours(0.0)

        self.sort_intervals()  # Ensure intervals are sorted

        for interval in self.intervals:
            # Calculate overlap window
            overlap_start = max(interval.start, start)
            overlap_end = min(interval.end, end)
            if overlap_start < overlap_end:
                # Calculate energy for the overlapping interval
                overlap_duration_sec = (overlap_end - overlap_start).total_seconds()
                interval_duration_sec = interval.duration.total_seconds()

                if interval_duration_sec > 0:
                    # Compute the energy ratio for the overlapping interval
                    ratio = overlap_duration_sec / interval_duration_sec
                    if interval.energy is not None:
                        # Ensure energy is not None before multiplying
                        total_energy = WattHours(total_energy + interval.energy * ratio)

        if total_energy > 0:
            return WattHours(round(total_energy, 3))  # Round to 3 decimal places
        return None  # No energy forecasted in the interval
