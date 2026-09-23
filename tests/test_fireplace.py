"""Focused regression checks; run with unittest (requires PyYAML and Jinja2)."""
from pathlib import Path
import unittest

import jinja2
import yaml


ROOT = Path(__file__).resolve().parents[1]


class PackageLoader(yaml.SafeLoader):
    pass


PackageLoader.add_constructor("!secret", lambda loader, node: loader.construct_scalar(node))
PACKAGE = yaml.load((ROOT / "modbus_lg_heatpump.yaml").read_text(encoding="utf-8"), Loader=PackageLoader)
AUTOMATIONS = {a["id"]: a for a in PACKAGE["automation"]}
SENSORS = {s["unique_id"]: s for group in PACKAGE["template"] for s in group.get("sensor", [])}


class FireplaceTests(unittest.TestCase):
    def setUp(self):
        self.states = {
            "sensor.hp_curve_raw": "28",
            "input_number.hp_curve_min_temp": "20",
            "input_number.hp_curve_shift": "0",
            "sensor.hp_solar_correction": "0",
            "sensor.hp_room_correction": "0",
            "input_boolean.hp_fireplace_mode": "on",
            "input_number.hp_fireplace_reduction": "3",
            "sensor.hp_auto_climate_mode": "Topení",
            "sensor.hp_climate_setpoint": "25",
            "input_number.hp_circuit1_target_temp": "28",
        }
        self.env = jinja2.Environment(undefined=jinja2.StrictUndefined)
        self.env.globals.update(
            states=lambda entity: self.states.get(entity, "unknown"),
            is_state=lambda entity, value: self.states.get(entity) == value,
        )

    def render(self, source, **kwargs):
        return self.env.from_string(source).render(**kwargs).strip()

    def setpoint(self):
        return int(self.render(SENSORS["hp_heating_curve_setpoint"]["state"]))

    def test_reduction_and_off(self):
        self.assertEqual(self.setpoint(), 25)
        self.states["input_boolean.hp_fireplace_mode"] = "off"
        self.assertEqual(self.setpoint(), 28)

    def test_minimum_and_hc1_limit(self):
        self.states["input_number.hp_fireplace_reduction"] = "10"
        self.states["input_number.hp_curve_min_temp"] = "24"
        self.assertEqual(self.setpoint(), 24)
        self.states["input_number.hp_curve_min_temp"] = "15"
        self.assertEqual(self.setpoint(), 20)

    def test_corrections_still_combine(self):
        self.states.update({"sensor.hp_solar_correction": "-2", "sensor.hp_room_correction": "3", "input_number.hp_curve_shift": "1"})
        self.assertEqual(self.setpoint(), 27)

    def test_zero_or_unavailable_reduction(self):
        for value in ("0", "unknown", "unavailable"):
            self.states["input_number.hp_fireplace_reduction"] = value
            self.assertEqual(self.setpoint(), 28)

    def test_write_timing(self):
        condition = AUTOMATIONS["hp_automation_apply_auto_climate_curve"]["condition"][-1]["value_template"]
        self.assertEqual(self.render(condition, trigger={"id": "setpoint"}), "True")
        self.states["input_boolean.hp_fireplace_mode"] = "off"
        self.assertEqual(self.render(condition, trigger={"id": "setpoint"}), "False")
        self.assertEqual(self.render(condition, trigger={"id": "timer"}), "True")
        self.states["sensor.hp_climate_setpoint"] = "28"
        self.states["input_number.hp_circuit1_target_temp"] = "25"
        self.assertEqual(self.render(condition, trigger={"id": "setpoint"}), "True")
        self.states["sensor.hp_auto_climate_mode"] = "Chlazení"
        for fireplace in ("on", "off"):
            self.states["input_boolean.hp_fireplace_mode"] = fireplace
            self.assertEqual(self.render(condition, trigger={"id": "setpoint"}), "False")

    def test_fireplace_no_longer_switches_or_blocks_floor(self):
        self.assertNotIn("hp_automation_fireplace_mode_on", AUTOMATIONS)
        resume = AUTOMATIONS["hp_automation_fireplace_mode_resume"]
        self.assertEqual([a["service"] for a in resume["action"]], ["input_boolean.turn_off"])
        for name in ("hp_automation_auto_climate_control", "hp_automation_auto_climate_water_hysteresis", "hp_automation_cutoff_turn_on"):
            automation = AUTOMATIONS[name]
            self.assertNotIn("input_boolean.hp_fireplace_mode", str(automation.get("condition")))
            self.assertNotIn("input_boolean.hp_fireplace_mode", str(automation["action"]))
        self.assertNotIn("hp_fireplace", SENSORS["hp_cooling_curve_setpoint"]["state"])

    def test_helper_and_dashboard(self):
        helper = PACKAGE["input_number"]["hp_fireplace_reduction"]
        self.assertEqual((helper["min"], helper["max"]), (0, 10))
        self.assertNotIn("initial", helper)
        dashboard = (ROOT / "dashboard_lg_heatpump.yaml").read_text(encoding="utf-8")
        yaml.safe_load(dashboard)
        self.assertEqual(dashboard.count("entity: input_number.hp_fireplace_reduction"), 2)


if __name__ == "__main__":
    unittest.main()
