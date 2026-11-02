import unittest

from leak_guard import iban_ok, luhn_ok, scan_text, scan_tree


class LeakGuardTest(unittest.TestCase):
    def test_example_domains_allowed(self):
        self.assertEqual(scan_text("a@example.com b@sub.example.org"), [])

    def test_real_looking_email_caught(self):
        self.assertEqual(scan_text("x ivana.k@mailbox-hr.net")[0][1], "email")

    def test_checksums(self):
        self.assertTrue(iban_ok("GB82 WEST 1234 5698 7654 32"))
        self.assertFalse(iban_ok("GB00 WEST 1234 5698 7654 32"))
        self.assertTrue(luhn_ok("4111 1111 1111 1111"))
        self.assertFalse(luhn_ok("4111 1111 1111 1112"))

    def test_fixtures(self):
        self.assertEqual(scan_tree("examples/clean_fixture", set()), [])
        kinds = sorted(h[2] for h in scan_tree("examples/leaky_fixture", set()))
        self.assertEqual(kinds, ["card", "email", "email", "email", "iban", "phone"])

    def test_allow_list(self):
        self.assertEqual(scan_text("+385 91 555 0199", allow={"+385 91 555 0199"}), [])


if __name__ == "__main__":
    unittest.main()
