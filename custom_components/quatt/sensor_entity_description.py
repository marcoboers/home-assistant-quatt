"""Sensor entity description for quatt."""
from homeassistant.components.sensor import SensorEntityDescription


class QuattSensorEntityDescription(SensorEntityDescription, frozen_or_thawed=True):
    """A class that describes Quatt sensor entities."""

    quatt_duo: bool = False
