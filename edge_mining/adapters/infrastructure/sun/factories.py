"""Collection of factories to create Sun."""

from datetime import datetime

from astral import LocationInfo
from astral.sun import sun, daylight, night, twilight, zenith_and_azimuth, elevation

from edge_mining.application.interfaces import SunFactoryInterface
from edge_mining.domain.policy.value_objects import Sun


class AstralSunFactory(SunFactoryInterface):
    """
    Factory to create Sun Value Objects using the astral library.
    """

    def __init__(
        self,
        latitude: float,
        longitude: float,
        timezone: str,
        name: str = "",
        region: str = "",
    ):
        """
        Initializes the factory with location information.
        """
        location_info = LocationInfo(
            name=name,
            region=region,
            timezone=timezone,
            latitude=latitude,
            longitude=longitude,
        )
        self._location = location_info

    def create_sun_for_date(self, for_date: datetime = datetime.now()) -> Sun:
        """
        Creates a Sun object for a specific date.
        """
        s = sun(self._location.observer, date=for_date)

        # Calculate night duration
        night_start, night_end = night(self._location.observer, date=for_date)
        night_duration = night_end - night_start

        # Obtain zenith and azimuth values
        zenith_value, azimuth_value = zenith_and_azimuth(self._location.observer, dateandtime=for_date)

        # Calculate daylight duration
        daylight_start, daylight_end = daylight(self._location.observer, date=for_date)
        daylight_duration = daylight_end - daylight_start

        # Calculate twilight duration
        twilight_start, twilight_end = twilight(self._location.observer, date=for_date)
        twilight_duration = twilight_end - twilight_start

        # Calculate elevation
        elevation_value = elevation(self._location.observer, dateandtime=for_date)

        return Sun(
            dawn=s["dawn"],
            sunrise=s["sunrise"],
            noon=s["noon"],
            midnight=s["midnight"],
            sunset=s["sunset"],
            dusk=s["dusk"],
            daylight=daylight_duration,
            night=night_duration,
            twilight=twilight_duration,
            azimuth=azimuth_value,
            zenith=zenith_value,
            elevation=elevation_value,
        )
