"""Support for Hyyp binary sensors."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import HyypDataUpdateCoordinator
from .entity import HyypSiteEntity, HyypPartitionEntity



BINARY_SENSOR_TYPES: dict[str, BinarySensorEntityDescription] = {
    "isMaster": BinarySensorEntityDescription(key="isMaster"),
    "hasPin": BinarySensorEntityDescription(key="hasPin"),
    "isOnline": BinarySensorEntityDescription(key="isOnline"),
}

PARALLEL_UPDATES = 1
async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up IDS Hyyp binary sensors based on a config entry."""
    coordinator: HyypDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        DATA_COORDINATOR
    ]

    async_add_entities(
        [
            HyypSensor(coordinator, site_id, sensor)
            for site_id in coordinator.data
            for sensor, value in coordinator.data[site_id].items()
            if sensor in BINARY_SENSOR_TYPES
            if value is not None        
        ]
    )
   
class HyypSensor(HyypSiteEntity, BinarySensorEntity):
    """Representation of a IDS Hyyp sensor."""

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
    """Represent the open/closed (violated/normal) state of an IDS zone."""

    _attr_device_class = BinarySensorDeviceClass.OPENING

    def __init__(
        self,
        coordinator: HyypDataUpdateCoordinator,
        site_id: int,
        partition_id: int,
        zone_id: str,
    ) -> None:
        """Initialize the zone status entity."""
        super().__init__(coordinator, site_id, partition_id)

        self._zone_id = zone_id
        zone = self._zone_data

        zone_name = zone.get("name") or f"Zone {zone_id}"

        self._attr_name = zone_name.title()
        self._attr_unique_id = (
            f"{self._site_id}_{self._partition_id}_{self._zone_id}_status"
        )

    @property
    def _zone_data(self) -> dict:
        """Return data for this zone."""
        return self.partition_data["zones"][self._zone_id]

    @property
    def is_on(self) -> bool:
        """Return True when zone is open or violated."""
        return bool(self._zone_data.get("openviolated", False))

    @property
    def extra_state_attributes(self) -> dict:
        """Return useful IDS zone metadata."""
        zone = self._zone_data

        return {
            "zone_id": self._zone_id,
            "zone_name": zone.get("name"),
            "partition_id": self._partition_id,
            "partition_name": self.partition_data.get("name"),
            "bypassed": bool(zone.get("bypassed", False)),
            "stay_bypassed": bool(zone.get("stay_bypassed", False)),
            "tampered": bool(zone.get("tampered", False)),
            "triggered": bool(zone.get("triggered", False)),
        }

class HyypZoneTriggerSensor(HyypPartitionEntity, BinarySensorEntity):
    """Representation of a IDS Hyyp sensor."""

    coordinator: HyypDataUpdateCoordinator

    def __init__(
        self,
        coordinator: HyypDataUpdateCoordinator,
        site_id: int,
        partition_id: int,
        zone_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, site_id, partition_id)
        self._sensor_name = f"{self.partition_data['zones'][zone_id]['name'].title()} trigger"
        self._zone_id = zone_id
        self._attr_name = f"{self.partition_data['zones'][zone_id]['name'].title()} trigger"
        self._attr_unique_id = f"{self._site_id}_{partition_id}_{zone_id}_trigger"
      
   
    @property
    def is_on(self) -> bool:
        """Return the state of the binary sensor."""
        return bool(self.partition_data["zones"][self._zone_id]["triggered"])
