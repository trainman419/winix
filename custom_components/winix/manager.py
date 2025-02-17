"""The Winix C545 Air Purifier component."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import List

from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from custom_components.winix.const import WINIX_DOMAIN
from custom_components.winix.device_wrapper import WinixDeviceWrapper
from custom_components.winix.helpers import Helpers
from winix import auth

_LOGGER = logging.getLogger(__name__)


class WinixEntity(CoordinatorEntity):
    """Winix entity."""

    def __init__(self, wrapper: WinixDeviceWrapper, coordinator: WinixManager) -> None:
        """Initialize the Winix entity."""
        super().__init__(coordinator)

        device_stub = wrapper.device_stub

        self._mac = device_stub.mac.lower()
        self._wrapper = wrapper
        self._name = f"Winix {device_stub.alias}"

        self._device_info: DeviceInfo = {
            "identifiers": {(WINIX_DOMAIN, self._mac)},
            "name": self._name,
            "manufacturer": "Winix",
            "model": device_stub.model,
            "sw_version": device_stub.sw_version,
        }

        self._attr_attribution = "Data provided by Winix"

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def device_info(self) -> DeviceInfo:
        """Return device specific attributes."""
        return self._device_info

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        state = self._wrapper.get_state()
        return state is not None


class WinixManager(DataUpdateCoordinator):
    """Representation of the Winix device manager."""

    def __init__(
        self,
        hass: HomeAssistant,
        auth_response: auth.WinixAuthResponse,
        scan_interval: int,
    ) -> None:
        """Initialize the manager."""

        self._device_wrappers: List[WinixDeviceWrapper] = None
        self._auth_response = auth_response

        super().__init__(
            hass,
            _LOGGER,
            name="WinixManager",
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self):
        await self.async_update()

    async def async_prepare_devices_wrappers(self) -> bool:
        """
        Prepare device wrappers.

        Raises WinixException.
        """

        device_stubs = await Helpers.async_get_device_stubs(
            self.hass, self._auth_response.access_token
        )

        if device_stubs:
            self._device_wrappers = []
            client = aiohttp_client.async_get_clientsession(self.hass)

            for device_stub in device_stubs:
                self._device_wrappers.append(
                    WinixDeviceWrapper(client, device_stub, _LOGGER)
                )

            _LOGGER.info("%d purifiers found", len(self._device_wrappers))
        else:
            _LOGGER.info("No purifiers found")

        return True

    async def async_update(self, now=None) -> None:
        # pylint: disable=unused-argument
        """Asynchronously update all the devices."""
        _LOGGER.info("Updating devices")
        for device_wrapper in self._device_wrappers:
            await device_wrapper.update()

    def get_device_wrappers(self) -> List[WinixDeviceWrapper]:
        """Return the device wrapper objects."""
        return self._device_wrappers
