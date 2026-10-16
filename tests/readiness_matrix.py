"""Exercise the installed CLI with isolated, synthetic credential stores."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class ReadinessMatrix(unittest.TestCase):
    def test_independent_credentials(self):
        binary = shutil.which(os.environ.get("HARN_BIN", "harn"))
        self.assertIsNotNone(binary, "a published Harn executable is required")
        checkout = Path(__file__).resolve().parent.parent
        for outbound, inbound in [(False, False), (True, False), (False, True), (True, True)]:
            with self.subTest(outbound=outbound, inbound=inbound), tempfile.TemporaryDirectory() as home:
                environment = {
                    "PATH": os.environ["PATH"],
                    "HOME": home,
                    "HARN_SECRET_PROVIDERS": "env",
                    "HARN_LLM_CALLS_DISABLED": "1",
                }
                if outbound:
                    environment["HARN_SECRET_NOTION_API_TOKEN"] = "synthetic-outbound"
                if inbound:
                    environment["HARN_SECRET_NOTION_VERIFICATION_TOKEN"] = "synthetic-inbound"
                result = subprocess.run(
                    [binary, "connect", "status", "--connector", "notion", "--run-health-checks", "--json"],
                    cwd=checkout,
                    env=environment,
                    capture_output=True,
                    text=True,
                    timeout=45,
                    check=True,
                )
                envelope = json.loads(result.stdout)
                self.assertIs(envelope["ok"], True)
                self.assertEqual(envelope["schemaVersion"], 1)
                rows = envelope["data"]["connectors"]
                self.assertEqual(len(rows), 1)
                row = rows[0]
                self.assertEqual(row["id"], "notion")
                self.assertIs(row["installed"], True)
                self.assertIs(row["usable"], outbound)
                self.assertEqual(row["status"], "healthy" if outbound else "missing_auth")
                self.assertEqual(row["missing_secrets"], [] if outbound else ["notion/api-token"])
                self.assertEqual(row["inbound"]["status"], "ready" if inbound else "missing_auth")
                self.assertEqual(row["inbound"]["required_secrets"], ["notion/verification-token"])
                self.assertEqual(
                    row["inbound"]["missing_secrets"],
                    [] if inbound else ["notion/verification-token"],
                )
                checks = {entry["id"]: entry["status"] for entry in row["health_checks"]}
                self.assertEqual(checks["api-token"], "pass" if outbound else "fail")
                self.assertEqual(checks["verification-token"], "pass" if inbound else "fail")


if __name__ == "__main__":
    unittest.main()
