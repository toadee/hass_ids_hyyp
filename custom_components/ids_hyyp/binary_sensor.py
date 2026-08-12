"""Support for IDS Hyyp binary sensors."""
from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import HyypDataUpdateCoordinator
from .entity import HyypPartitionEntity, HyypSiteEntity

BINARY_SENSOR_TYPES: dict[str, BinarySensorEntityDescription] = {
    "isMaster": BinarySensorEntityDescription(key="isMaster"),
    "hasPin": BinarySensorEntityDescription(key="hasPin"),
    "isOnline": BinarySensorEntityDescription(
        key="isOnline",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
}

# The IDS API does not provide a reliable sensor hardware/type field.
# These are per-panel mappings based on the installed physical hardware.
ZONE_DEVICE_CLASSES_BY_NAME: dict[str, BinarySensorDeviceClass | None] = {
    "FRONT DOOR": BinarySensorDeviceClass.DOOR,
    "BACK SLIDER": BinarySensorDeviceClass.DOOR,
    "LOUNGE": BinarySensorDeviceClass.MOTION,
    "MBED KITCHEN": BinarySensorDeviceClass.MOTION,
    "NURSARY": BinarySensorDeviceClass.MOTION,
    "OFFICE": BinarySensorDeviceClass.MOTION,
}

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up IDS Hyyp binary sensors based on a config entry."""
    coordinator: HyypDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        DATA_COORDINATOR
    ]

    # Existing site-level binary sensors.
    async_add_entities(
        [
            HyypSensor(coordinator, site_id, sensor)
            for site_id, site_data in coordinator.data.items()
            for sensor, value in site_data.items()
            if sensor in BINARY_SENSOR_TYPES
            if value is not None
        ]
    )

    # One current-state binary sensor for every IDS zone.
    async_add_entities(
        [
            HyypZoneStatusSensor(coordinator, site_id, partition_id, zone_id)
            for site_id, site_data in coordinator.data.items()
            for partition_id, partition_data in site_data.get("partitions", {}).items()
            for zone_id in partition_data.get("zones", {})
        ]
    )


class HyypSensor(HyypSiteEntity, BinarySensorEntity):
    """Representation of an IDS Hyyp site binary sensor."""

    coordinator: HyypDataUpdateCoordinator

    def __init__(
        self,
        coordinator: HyypDataUpdateCoordinator,
        site_id: int,
        binary_sensor: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, site_id)
        self._sensor_name = binary_sensor
        self._attr_name = f"{self.data['name']} {binary_sensor.title()}"
        self._attr_unique_id = f"{self._site_id}_{binary_sensor}"
        self.entity_description = BINARY_SENSOR_TYPES[binary_sensor]

    @property
    def is_on(self) -> bool:
        """Return the state of the binary sensor."""
        return bool(self.data[self._sensor_name])


class HyypZoneStatusSensor(HyypPartitionEntity, BinarySensorEntity):
    """Represent the current normal/violated state of an IDS zone."""

    coordinator: HyypDataUpdateCoordinator

    def __init__(
        self,
        coordinator: HyypDataUpdateCoordinator,
        site_id: int,
        partition_id: int,
        zone_id: str,
    ) -> None:
        """Initialize the zone status sensor."""
        super().__init__(coordinator, site_id, partition_id)

        self._zone_id = zone_id
        zone = self._zone_data
        zone_name = zone.get("name") or f"Zone {zone_id}"

        self._attr_name = zone_name.title()
        self._attr_unique_id = (
            f"{self._site_id}_{self._partition_id}_{self._zone_id}_status"
        )

        if zone_name.strip().upper() in ZONE_DEVICE_CLASSES_BY_NAME:
            device_class = ZONE_DEVICE_CLASSES_BY_NAME[zone_name.strip().upper()]
            if device_class is not None:
                self._attr_device_class = device_class

    @property
    def _zone_data(self) -> dict[str, Any]:
        """Return the latest coordinator data for this zone."""
        return self.partition_data["zones"][self._zone_id]

    @property
    def is_on(self) -> bool:
        """Return True when IDS reports this zone as violated."""
        return bool(self._zone_data.get("openviolated", False))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return IDS zone data that is useful for dashboards and automations."""
        zone = self._zone_data

        return {
            "zone_id": self._zone_id,
            "partition_id": self._partition_id,
            "partition_name": self.partition_data.get("name"),
            "bypassed": bool(zone.get("bypassed", False)),
            "stay_bypassed": bool(zone.get("stay_bypassed", False)),
            "tampered": bool(zone.get("tampered", False)),
            "triggered": bool(zone.get("triggered", False)),
        }
