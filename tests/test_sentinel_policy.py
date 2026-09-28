import unittest

from prestige_core.sentinel_policy import ProtectionPolicy
from tests.test_sentinel_firewall import FakeFirewall
from prestige_core.sentinel_firewall import change_block


def alert(address, epoch, severity="HIGH"):
    return {"source": address, "epoch": epoch, "severity": severity}


class ProtectionPolicyTests(unittest.TestCase):
    def test_two_high_alerts_and_reversible_backend(self):
        policy = ProtectionPolicy(trusted=["192.168.1.60"], local=["192.168.1.2"])
        self.assertEqual(policy.consider(alert("192.168.1.50", 10))["status"], "OBSERVE")
        self.assertEqual(policy.consider(alert("192.168.1.50", 15))["status"], "OBSERVE")
        decision = policy.consider(alert("192.168.1.50", 31))
        self.assertEqual(decision["status"], "BLOCK")
        backend = FakeFirewall()
        self.assertEqual(change_block(decision["address"], backend, enable=True, apply=True)["status"], "BLOCKED")
        self.assertEqual(change_block(decision["address"], backend, enable=False, apply=True)["status"], "UNBLOCKED")
        self.assertEqual(policy.consider(alert("192.168.1.50", 52))["status"], "IGNORE")

    def test_trusted_local_special_and_medium_are_ignored(self):
        policy = ProtectionPolicy(trusted=["192.168.1.60"], local=["192.168.1.2"])
        for address in ("192.168.1.60", "192.168.1.2", "127.0.0.1", "224.0.0.1"):
            self.assertEqual(policy.consider(alert(address, 1))["status"], "IGNORE")
        self.assertEqual(policy.consider(alert("192.168.1.50", 1, "MEDIUM"))["status"], "IGNORE")

    def test_limit_and_failed_action_reset(self):
        policy = ProtectionPolicy(max_blocks=1)
        policy.consider(alert("192.168.1.50", 1))
        self.assertEqual(policy.consider(alert("192.168.1.50", 22))["status"], "BLOCK")
        policy.consider(alert("192.168.1.51", 1))
        self.assertEqual(policy.consider(alert("192.168.1.51", 22))["status"], "LIMIT")
        policy.release("192.168.1.50")
        self.assertEqual(policy.consider(alert("192.168.1.50", 43))["status"], "OBSERVE")


if __name__ == "__main__":
    unittest.main()
