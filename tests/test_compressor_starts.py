"""Verify persistent start counting and the migration away from recorder history."""
import math
import unittest

import jinja2
import yaml

from test_fireplace import AUTOMATIONS, PACKAGE, ROOT, SENSORS


def is_number(value):
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


class CompressorStartsTests(unittest.TestCase):
    def test_period_counts_use_persistent_total_instead_of_history(self):
        # Purging binary-sensor history must not be able to change these counts.
        history_counts = [
            sensor for sensor in PACKAGE["sensor"]
            if sensor.get("platform") == "history_stats"
            and sensor.get("entity_id") == "binary_sensor.hp_compressor_status"
        ]
        self.assertEqual(history_counts, [])
        for cycle in ("daily", "weekly", "monthly", "yearly"):
            with self.subTest(cycle=cycle):
                meter = PACKAGE["utility_meter"]["hp_compressor_starts_" + cycle]
                self.assertEqual(meter["source"], "sensor.hp_compressor_starts_total")
                self.assertEqual(meter["cycle"], cycle)
                self.assertFalse(meter.get("net_consumption", False))
                self.assertFalse(meter.get("delta_values", False))
                # Recover differences across source unavailability, hold the total.
                self.assertFalse(meter["periodically_resetting"])
                self.assertTrue(meter["always_available"])
                self.assertNotIn("cron", meter)
                self.assertNotIn("offset", meter)
        self.assertTrue(PACKAGE["counter"]["hp_compressor_starts_total"]["restore"])

    def test_source_unavailability_is_not_published_as_zero(self):
        sensor = SENSORS["hp_compressor_starts_total_sensor"]
        env = jinja2.Environment(undefined=jinja2.StrictUndefined)
        env.globals["is_number"] = is_number
        for value, available in (("297", True), ("298", True), ("0", True),
                                 ("unknown", False), ("unavailable", False)):
            with self.subTest(value=value):
                env.globals["states"] = lambda entity: value
                rendered = env.from_string(sensor["availability"]).render().strip()
                self.assertEqual(rendered, str(available))
                if available:
                    self.assertEqual(int(env.from_string(sensor["state"]).render()), int(value))

    def test_only_observed_off_to_on_counts_as_a_start(self):
        automation = AUTOMATIONS["hp_automation_compressor_start_counter"]
        self.assertEqual(len(automation["trigger"]), 1)
        trigger = automation["trigger"][0]
        self.assertEqual(trigger["platform"], "state")
        self.assertEqual(trigger["entity_id"], "binary_sensor.hp_compressor_status")
        self.assertEqual((trigger["from"], trigger["to"]), ("off", "on"))
        self.assertEqual(automation["action"], [{
            "service": "counter.increment",
            "target": {"entity_id": "counter.hp_compressor_starts_total"},
        }])

    def test_dashboard_uses_new_meters_without_entity_registry_collisions(self):
        dashboard = yaml.safe_load((ROOT / "dashboard_lg_heatpump.yaml").read_text(encoding="utf-8"))

        def find_start_cards(node):
            if isinstance(node, dict):
                if node.get("title") == "Počty startů":
                    yield node
                for value in node.values():
                    yield from find_start_cards(value)
            elif isinstance(node, list):
                for value in node:
                    yield from find_start_cards(value)

        cards = list(find_start_cards(dashboard))
        self.assertEqual(len(cards), 1)
        self.assertEqual([row["entity"] for row in cards[0]["entities"]], [
            "sensor.hp_compressor_starts_" + cycle
            for cycle in ("daily", "weekly", "monthly", "yearly")
        ])
        for cycle in ("daily", "weekly", "monthly", "yearly"):
            meter = PACKAGE["utility_meter"]["hp_compressor_starts_" + cycle]
            # Utility Meter generates the initial entity_id from its name.
            self.assertEqual(meter["name"].lower().replace(" ", "_"),
                             "hp_compressor_starts_" + cycle)


if __name__ == "__main__":
    unittest.main()
