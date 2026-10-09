import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
import zipfile

from prestige_core.archive_inspector import inspect_archive
from prestige_core.virustotal_lookup import hash_file, lookup_hash
from prestige_core.system_optimization import interpret
from prestige_core.persistence_overview import overview


class SecurityAdditionsTests(unittest.TestCase):
    def test_zip_metadata_flags_without_extracting(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sample.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("../danger.exe", b"example")
                archive.writestr("readme.txt", b"hello")
            result = inspect_archive(path)
            self.assertEqual(result["kind"], "ZIP")
            self.assertEqual(result["entries_shown"], 2)
            self.assertIn("PATH_ESCAPE", result["entries"][0]["flags"])
            self.assertIn("EXECUTABLE_NAME", result["entries"][0]["flags"])
            self.assertFalse((Path(folder) / "danger.exe").exists())

    def test_tar_link_flag_without_extracting(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sample.tar"
            with tarfile.open(path, "w") as archive:
                link = tarfile.TarInfo("shortcut")
                link.type = tarfile.SYMTYPE
                link.linkname = "../../outside"
                archive.addfile(link)
            result = inspect_archive(path)
            self.assertIn("LINK", result["entries"][0]["flags"])

    def test_virustotal_hash_only_request(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "file.bin"
            path.write_bytes(b"hello")
            digest = hash_file(path)
            seen = []
            class Response:
                def __enter__(self):
                    return io.BytesIO(json.dumps({"data": {"attributes": {
                        "last_analysis_stats": {"malicious": 0, "suspicious": 1}}}}).encode())
                def __exit__(self, *_args):
                    return False
            def opener(request, timeout):
                seen.append((request.full_url, request.get_method(), request.data))
                return Response()
            result = lookup_hash(digest, api_key="test-key", opener=opener)
            self.assertEqual(result["status"], "FOUND")
            self.assertEqual(seen, [("https://www.virustotal.com/api/v3/files/" + digest,
                                     "GET", None)])

    def test_optimization_does_not_recommend_disabling_updates(self):
        data = {"startup": {"status": "OK", "data": [{"Name": "Example"}]},
                "edge_processes": {"status": "OK", "data": [{"Id": 1}]},
                "updates": {"status": "OK", "data": [{"StartType": "Disabled"}]}}
        result = interpret(data)
        self.assertTrue(result["read_only"])
        self.assertIn("przywróć aktualizacje", str(result["findings"]))

    def test_persistence_overview_marks_missing_evidence_unknown(self):
        result = overview({"evidence": {"processes": {"status": "OK", "data": [
            {"pid": 7}]}}, "alerts": [], "correlations": []})
        self.assertEqual(result["areas"][0]["items"], 1)
        self.assertEqual(result["areas"][1]["status"], "UNKNOWN")
        self.assertEqual(result["firmware"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
