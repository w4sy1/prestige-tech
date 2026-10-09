import base64
from datetime import date
import json
from pathlib import Path
import tempfile
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from prestige_core.offline_license import (DOMAIN, _canonical, create_issuer_keys,
                                           issue_license, verify_license)


class OfflineLicenseTests(unittest.TestCase):
    def test_issuer_roundtrip_keeps_private_key_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            private = Path(directory) / "owner-private.pem"
            public = Path(directory) / "pro-public.pem"
            license_file = Path(directory) / "customer.json"
            create_issuer_keys(private, public, "fixture-password-long")
            self.assertNotIn(b"PRIVATE KEY", public.read_bytes())
            issue_license(private, "fixture-password-long", "customer-1234",
                          "2030-12-31", license_file)
            self.assertEqual(verify_license(license_file, public.read_bytes(),
                                            today=date(2029, 1, 1))["license_id"], "customer-1234")
            with self.assertRaises(FileExistsError):
                create_issuer_keys(private, public, "fixture-password-long")

    def test_signature_expiry_and_tampering(self):
        private = Ed25519PrivateKey.generate()
        public = private.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        payload = {"schema_version": 1, "edition": "PRO", "license_id": "fixture-1234",
                   "expires": "2030-01-01"}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "license.json"
            record = {"payload": payload, "signature": base64.b64encode(
                private.sign(DOMAIN + _canonical(payload))).decode("ascii")}
            path.write_text(json.dumps(record), encoding="utf-8")
            self.assertEqual(verify_license(path, public, today=date(2029, 1, 1))["edition"], "PRO")
            with self.assertRaises(ValueError):
                verify_license(path, public, today=date(2030, 1, 2))
            record["payload"]["edition"] = "FREE"
            path.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_license(path, public, today=date(2029, 1, 1))
