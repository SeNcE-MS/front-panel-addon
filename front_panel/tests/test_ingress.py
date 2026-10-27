import copy,json,tempfile,threading,unittest,urllib.request,urllib.error
from pathlib import Path
import server

class IngressEditorTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.srv=server.create_server(('127.0.0.1',0),trusted_peers={'127.0.0.1'},data_dir=Path(self.tmp.name))
        threading.Thread(target=self.srv.serve_forever,daemon=True).start()
        self.base=f'http://127.0.0.1:{self.srv.server_port}'
        self.headers={'X-Ingress-Path':'/api/hassio_ingress/test-session','Origin':'https://ha.example.invalid'}
    def tearDown(self):self.srv.shutdown();self.srv.server_close();self.tmp.cleanup()
    def test_ha_ingress_opens_editor_without_separate_password(self):
        req=urllib.request.Request(self.base+'/editor',headers=self.headers)
        self.assertIn('editor-form',urllib.request.urlopen(req).read().decode())
    def test_ingress_save_and_readback(self):
        config=copy.deepcopy(server.DEFAULT);config['title']='애드온 편집 테스트'
        req=urllib.request.Request(self.base+'/api/config',method='PUT',headers={**self.headers,'Content-Type':'application/json'},data=json.dumps(config).encode())
        self.assertTrue(json.load(urllib.request.urlopen(req))['saved'])
        req=urllib.request.Request(self.base+'/api/config',headers=self.headers)
        self.assertEqual(json.load(urllib.request.urlopen(req))['title'],config['title'])
    def test_ingress_root_redirects_to_editor(self):
        req=urllib.request.Request(self.base+'/',headers=self.headers)
        response=urllib.request.urlopen(req)
        self.assertTrue(response.url.endswith('/editor'))
    def test_missing_ingress_path_cannot_edit(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:urllib.request.urlopen(self.base+'/editor')
        self.assertIn(ctx.exception.code,[401,403])
