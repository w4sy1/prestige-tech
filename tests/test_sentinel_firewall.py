import unittest

from prestige_core.sentinel_firewall import change_block, rule_name


class FakeFirewall:
    def __init__(self):
        self.rules = {}
        self.fail_direction = None
        self.protected = ["192.168.1.1", "192.168.1.2", "2001:db8::1"]

    def protected_addresses(self):
        return self.protected

    def get(self, name):
        return self.rules.get(name)

    def add(self, name, address, direction):
        if direction == self.fail_direction:
            raise RuntimeError("fixture failure")
        self.rules[name] = {"name": name, "remote": address, "direction": direction,
                            "action": "Block", "description": "Prestige Tech Network Sentinel"}

    def remove(self, name):
        self.rules.pop(name)


class SentinelFirewallTest(unittest.TestCase):
    def test_plan_apply_and_unblock_only_own_rules(self):
        backend = FakeFirewall()
        plan = change_block("192.168.1.50", backend, enable=True)
        self.assertEqual(plan["status"], "PLAN")
        self.assertEqual(len(backend.rules), 0)
        self.assertEqual(change_block("192.168.1.50", backend, enable=True, apply=True)["status"], "BLOCKED")
        self.assertEqual(len(backend.rules), 2)
        self.assertEqual(change_block("192.168.1.50", backend, enable=True, apply=True)["changed"], [])
        self.assertEqual(change_block("192.168.1.50", backend, enable=False, apply=True)["status"], "UNBLOCKED")
        self.assertEqual(len(backend.rules), 0)

    def test_protects_system_addresses_and_foreign_rule(self):
        backend = FakeFirewall()
        for ip in ("192.168.1.1", "192.168.1.2", "127.0.0.1", "224.0.0.1",
                   "240.0.0.1", "255.255.255.255"):
            with self.subTest(ip=ip), self.assertRaises(ValueError):
                change_block(ip, backend, enable=True, apply=True)
        name = rule_name("192.168.1.50", "Inbound")
        backend.rules[name] = {"name": name, "remote": "192.168.1.51"}
        with self.assertRaises(RuntimeError):
            change_block("192.168.1.50", backend, enable=False, apply=True)

    def test_second_rule_failure_rolls_back_first(self):
        backend = FakeFirewall()
        backend.fail_direction = "Outbound"
        with self.assertRaises(RuntimeError):
            change_block("192.168.1.50", backend, enable=True, apply=True)
        self.assertEqual(backend.rules, {})

    def test_error_after_second_create_still_rolls_back_both(self):
        class AmbiguousBackend(FakeFirewall):
            def add(self, name, address, direction):
                super().add(name, address, direction)
                if direction == "Outbound":
                    raise RuntimeError("response lost after creation")
        backend = AmbiguousBackend()
        with self.assertRaises(RuntimeError):
            change_block("192.168.1.50", backend, enable=True, apply=True)
        self.assertEqual(backend.rules, {})
