"""Regression checks for defrost accounting (requires PyYAML and Jinja2)."""
import unittest

import jinja2

from test_fireplace import PACKAGE, SENSORS


BINARY_SENSORS = {
    sensor["unique_id"]: sensor
    for group in PACKAGE["template"]
    for sensor in group.get("binary_sensor", [])
}


class DefrostTests(unittest.TestCase):
    def setUp(self):
        self.states = {
            "sensor.hp_operation_mode": "4",
            "binary_sensor.hp_compressor_status": "on",
            "binary_sensor.hp_dhw_heating_status": "off",
            "binary_sensor.hp_defrosting_status": "off",
            "binary_sensor.hp_heating_active_by_delta": "on",
            "binary_sensor.hp_cooling_active_by_delta": "off",
            "sensor.hp_flow_rate": "15",
            "sensor.hp_delta_temp": "3",
            "sensor.hp_thermal_power": "3140",
            "sensor.hp_cop_carnot": "20",
            "sensor.shellypro3em_a4f00fcfb120_vykon": "1000",
            "sensor.shellypro3em_a4f00fcfb120_phase_a_vykon": "800",
            "sensor.shellypro3em_a4f00fcfb120_phase_c_vykon": "200",
        }
        self.env = jinja2.Environment(undefined=jinja2.StrictUndefined)
        self.env.globals.update(
            states=lambda entity: self.states.get(entity, "unknown"),
            is_state=lambda entity, value: self.states.get(entity) == value,
        )

    def render(self, template):
        return self.env.from_string(template).render().strip()

    def sensor(self, name):
        return float(self.render(SENSORS[name]["state"]))

    def cooling_detected(self):
        return self.render(BINARY_SENSORS["hp_cooling_active_by_delta"]["state"]) == "True"

    def assert_electrical_split(self, dhw=0, heating=0, cooling=0, other=0):
        values = []
        for mode, expected in zip(("dhw", "heating", "cooling", "other"), (dhw, heating, cooling, other)):
            value = self.sensor("hp_electrical_power_" + mode)
            self.assertEqual(value, expected, mode)
            values.append(value)
        self.assertEqual(sum(values), 1000)

    def test_heating_defrost_and_recovery(self):
        self.assert_electrical_split(heating=1000)
        for heating_active in ("on", "off"):
            with self.subTest(heating_active=heating_active):
                self.states.update({
                    "binary_sensor.hp_defrosting_status": "on",
                    "binary_sensor.hp_heating_active_by_delta": heating_active,
                    "sensor.hp_delta_temp": "-3",
                })
                self.assertFalse(self.cooling_detected())
                self.assert_electrical_split(heating=1000)
                self.assertEqual(self.sensor("hp_thermal_power"), 0)
        # Po skončení odmrazování může voda ještě krátce mít zápornou deltu.
        self.states["binary_sensor.hp_defrosting_status"] = "off"
        self.assertFalse(self.cooling_detected())
        self.states.update({
            "binary_sensor.hp_heating_active_by_delta": "on",
            "sensor.hp_delta_temp": "3",
        })
        self.assert_electrical_split(heating=1000)
        self.assertGreater(self.sensor("hp_thermal_power"), 0)

    def test_delayed_cooling_sensor_cannot_count_defrost(self):
        # Zastaralé stavy kvůli delay_off i rozdílnému pořadí aktualizací.
        self.states.update({
            "sensor.hp_operation_mode": "3",
            "binary_sensor.hp_defrosting_status": "on",
            "binary_sensor.hp_cooling_active_by_delta": "on",
            "binary_sensor.hp_heating_active_by_delta": "off",
            "sensor.hp_delta_temp": "-3",
        })
        self.assertFalse(self.cooling_detected())
        self.assert_electrical_split(heating=1000)
        for sensor in ("hp_cop_cooling", "hp_thermal_power_cooling", "hp_thermal_power"):
            self.assertEqual(self.sensor(sensor), 0)

    def test_real_cooling_in_manual_and_auto_modes(self):
        self.states.update({
            "binary_sensor.hp_heating_active_by_delta": "off",
            "binary_sensor.hp_cooling_active_by_delta": "on",
            "sensor.hp_delta_temp": "-3",
        })
        for mode in ("0", "3"):
            with self.subTest(mode=mode):
                self.states["sensor.hp_operation_mode"] = mode
                self.assertTrue(self.cooling_detected())
                self.assert_electrical_split(cooling=1000)
                self.assertEqual(self.sensor("hp_thermal_power_cooling"), 3140)
                self.assertEqual(self.sensor("hp_cop_cooling"), 3.14)

    def test_heating_mode_blocks_residual_cooling(self):
        self.states.update({
            "binary_sensor.hp_cooling_active_by_delta": "on",
            "sensor.hp_delta_temp": "-3",
        })
        self.assertFalse(self.cooling_detected())
        self.assert_electrical_split(heating=1000)
        self.assertEqual(self.sensor("hp_thermal_power_cooling"), 0)
        self.assertEqual(self.sensor("hp_cop_cooling"), 0)

    def test_dhw_has_priority_during_defrost(self):
        self.states.update({
            "binary_sensor.hp_dhw_heating_status": "on",
            "binary_sensor.hp_defrosting_status": "on",
            "binary_sensor.hp_cooling_active_by_delta": "on",
        })
        self.assertFalse(self.cooling_detected())
        self.assert_electrical_split(dhw=1000)
        self.assertEqual(self.sensor("hp_thermal_power"), 0)

    def test_idle_power_stays_other(self):
        self.states.update({
            "binary_sensor.hp_compressor_status": "off",
            "binary_sensor.hp_heating_active_by_delta": "off",
        })
        self.assertFalse(self.cooling_detected())
        self.assert_electrical_split(other=1000)
        self.assertEqual(self.sensor("hp_thermal_power"), 0)

    def test_cooling_requires_known_defrost_and_operation_mode(self):
        self.states["sensor.hp_delta_temp"] = "-3"
        for mode in ("4", "unknown", "unavailable"):
            self.states["sensor.hp_operation_mode"] = mode
            self.assertFalse(self.cooling_detected())
        self.states["sensor.hp_operation_mode"] = "0"
        for defrost in ("on", "unknown", "unavailable"):
            self.states["binary_sensor.hp_defrosting_status"] = defrost
            self.assertFalse(self.cooling_detected())


if __name__ == "__main__":
    unittest.main()
