import sys
import threading
import unittest
import urllib.request
import urllib.error
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

class ServerTest(unittest.TestCase):
    def test_demo_serves_without_ha_credentials(self):
        import server
        srv = server.create_server(('127.0.0.1', 0), trusted_peers={'127.0.0.1'})
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{srv.server_port}/') as response:
                self.assertEqual(response.status, 200)
                self.assertIn('미리보기', response.read().decode())
                self.assertIn("default-src 'self'", response.headers['Content-Security-Policy'])
        finally:
            srv.shutdown()
            srv.server_close()

    def test_local_korean_font_available(self):
        import server
        srv = server.create_server(('127.0.0.1', 0), trusted_peers={'127.0.0.1'})
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{srv.server_port}/panel-ko.ttf') as response:
                self.assertEqual(response.headers['Content-Type'], 'font/ttf')
                self.assertGreater(len(response.read()), 1000)
        finally:
            srv.shutdown()
            srv.server_close()

    def test_direct_access_and_spoofed_header_blocked(self):
        import server
        srv = server.create_server(('127.0.0.1', 0))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            req = urllib.request.Request(f'http://127.0.0.1:{srv.server_port}/api/config', headers={'X-Forwarded-For':'172.30.32.2'})
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(req)
            self.assertEqual(ctx.exception.code, 401)
        finally:
            srv.shutdown()
            srv.server_close()

    def test_unknown_and_traversal_paths_rejected(self):
        import server
        srv = server.create_server(('127.0.0.1', 0), trusted_peers={'127.0.0.1'})
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            for path in ['/../server.py', '/%2e%2e/server.py', '/data/options.json', '/api/control']:
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    urllib.request.urlopen(f'http://127.0.0.1:{srv.server_port}{path}')
                self.assertEqual(ctx.exception.code, 404)
        finally:
            srv.shutdown()
            srv.server_close()

if __name__ == '__main__':
    unittest.main()
