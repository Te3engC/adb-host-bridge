import socketserver
import threading
import unittest
from unittest.mock import patch

from adb_host_bridge.adb_proxy import PINNED_ADB_BINARY, resolve_adb_binary
from adb_host_bridge.discovery import Endpoint, list_devices, parse_endpoint, probe


class FakeAdbHandler(socketserver.BaseRequestHandler):
    def handle(self):
        length = int(self.request.recv(4), 16)
        service = self.request.recv(length).decode("ascii")
        responses = {
            "host:version": "0029",
            "host:devices-l": "SERIAL123\tdevice product:test model:Demo device:demo transport_id:1\n",
        }
        response = responses[service].encode("utf-8")
        self.request.sendall(b"OKAY" + f"{len(response):04x}".encode("ascii") + response)


class DiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), FakeAdbHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def endpoint(self):
        host, port = self.server.server_address
        return Endpoint(host, port, "test")

    def test_parse_endpoint(self):
        self.assertEqual(parse_endpoint("tcp:10.0.0.2:5040").host, "10.0.0.2")
        self.assertEqual(parse_endpoint("tcp:10.0.0.2:5040").port, 5040)
        self.assertEqual(parse_endpoint("host.local").port, 5037)

    def test_probe_validates_adb_protocol(self):
        self.assertEqual(probe(self.endpoint()).version, "41")

    def test_list_devices_without_adb_binary(self):
        self.assertIn("SERIAL123\tdevice", list_devices(self.endpoint()))

    def test_default_client_is_pinned(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(resolve_adb_binary(), str(PINNED_ADB_BINARY))


if __name__ == "__main__":
    unittest.main()
