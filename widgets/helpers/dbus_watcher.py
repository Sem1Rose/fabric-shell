import dbus  # pip install dbus-python
import dbus.mainloop.glib
from typing import Literal
from fabric import Service, Property, Signal
from loguru import logger

DBUS_PROPERTIES_IFACE = "org.freedesktop.DBus.Properties"
SYSTEMD_MANAGER_IFACE = "org.freedesktop.systemd1.Manager"
SYSTEMD_UNIT_IFACE = "org.freedesktop.systemd1.Unit"

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)


class UnitsMonitor(Service):
    @Property(list[str], flags="readable")
    def active_units(self) -> list[str]:
        return [k for k, v in self._units.items() if v == "active"]

    @Property(list[str], flags="readable")
    def failed_units(self) -> list[str]:
        return [k for k, v in self._units.items() if v == "failed"]

    @Property(dict[str, str], flags="read-write")
    def units(self) -> dict[str, str]:
        return self._units

    @units.setter
    def units(self, value: dict[str, str]):
        self._units = value
        return

    @Signal
    def unit_status(self, unit_name: str, status: str):
        self.notify("units")
        self.notify("active-units")
        self.notify("failed-units")
        return

    def __init__(
        self,
        units: list[str],
        bus_type: Literal["session", "system"] = "session",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._units = {}

        self._bus = dbus.SessionBus() if bus_type == "session" else dbus.SystemBus()
        self._proxy = self._bus.get_object(
            "org.freedesktop.systemd1", "/org/freedesktop/systemd1"
        )
        self._manager = dbus.Interface(
            self._proxy, dbus_interface=SYSTEMD_MANAGER_IFACE
        )

        self._unit_paths = {}
        for unit in units:
            try:
                path = self._manager.GetUnit(unit)
            except dbus.DBusException as e:
                logger.error(
                    f"couldn't find unit `{unit}`: {e.get_dbus_message()}",
                )
                continue
            self._unit_paths[unit] = path

            state = self.fetch_unit_status(unit)

            self.units[unit] = state
            self.unit_status(unit, state)

        for unit, path in self._unit_paths.items():
            self._bus.add_signal_receiver(
                handler_function=lambda iface,
                changed,
                _,
                name=unit: self.on_dbus_property_changed(iface, changed, name),
                signal_name="PropertiesChanged",
                dbus_interface=DBUS_PROPERTIES_IFACE,
                path=path,
                arg0=SYSTEMD_UNIT_IFACE,
            )

    def on_dbus_property_changed(
        self, interface: str, props: dict[str, str], unit_name: str, *_
    ):
        if (
            interface != SYSTEMD_UNIT_IFACE
            or "ActiveState" not in props
            or (new_state := str(props["ActiveState"])) == self.units[unit_name]
        ):
            return

        self.units[unit_name] = new_state
        self.unit_status(unit_name, new_state)
        return

    def fetch_unit_status(self, unit_name: str) -> Literal["failed", "active"]:
        unit_proxy = self._bus.get_object(
            "org.freedesktop.systemd1", self._unit_paths[unit_name]
        )
        props = dbus.Interface(unit_proxy, dbus_interface=DBUS_PROPERTIES_IFACE)
        state = str(props.Get(SYSTEMD_UNIT_IFACE, "ActiveState"))

        return state  # type: ignore
