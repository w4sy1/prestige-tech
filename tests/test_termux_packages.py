import unittest

from prestige_core.termux_packages import compare_profile_packages


class TermuxPackagesTest(unittest.TestCase):
    def test_profile_diff_uses_read_only_dpkg_query(self):
        commands = []
        def runner(command, timeout):
            commands.append(command)
            return "git\npython\n"
        result = compare_profile_packages("minimal", runner=runner,
                                          environ={"PREFIX": "/data/data/com.termux/files/usr"})
        self.assertEqual(commands[0][0], "dpkg-query")
        self.assertEqual(result["installed"], ["git", "python"])
        self.assertEqual(result["missing"], ["curl", "nano"])
        with self.assertRaises(RuntimeError):
            compare_profile_packages("minimal", runner=runner, environ={"PREFIX": ""})


if __name__ == "__main__":
    unittest.main()
