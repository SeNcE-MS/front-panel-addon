import copy,json,tempfile,threading,unittest,urllib.request,urllib.error,http.cookiejar
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server

class DirectPanelTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.srv=server.create_server(('127.0.0.1',0),trusted_peers=set(),data_dir=Path(self.tmp.name),passwords={'viewer':'viewer-test-password','editor':'editor-test-password'})
        threading.Thread(target=self.srv.serve_forever,daemon=True).start()
        self.base=f'http://127.0.0.1:{self.srv.server_port}'
        self.client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def tearDown(self):
        self.srv.shutdown();self.srv.server_close();self.tmp.cleanup()
    def login(self,role):
        return self.client.open(urllib.request.Request(self.base+'/api/login',data=json.dumps({'role':role,'password':role+'-test-password'}).encode(),headers={'Content-Type':'application/json','Origin':self.base}))
    def save(self,config):
        return self.client.open(urllib.request.Request(self.base+'/api/config',method='PUT',data=json.dumps(config).encode(),headers={'Content-Type':'application/json','Origin':self.base}))
    def test_anonymous_cannot_read_config_or_editor(self):
        for p in ['/api/config','/editor','/editor.js','/app.js']:
            with self.assertRaises(urllib.error.HTTPError) as ctx:self.client.open(self.base+p)
            self.assertIn(ctx.exception.code,[401,403])
    def test_anonymous_appearance_write_blocked(self):
        req=urllib.request.Request(self.base+'/api/appearance',method='POST',data=b'{"color_mode":"light"}',headers={'Origin':self.base,'Content-Type':'application/json'})
        with self.assertRaises(urllib.error.HTTPError) as ctx:self.client.open(req)
        self.assertEqual(ctx.exception.code,401)
    def test_viewer_direct_access_and_editor_isolation(self):
        self.login('viewer')
        html=self.client.open(self.base+'/').read().decode()
        self.assertIn('app.js',html);self.assertNotIn('editor.js',html)
        config=json.load(self.client.open(self.base+'/api/config'))
        with self.assertRaises(urllib.error.HTTPError) as ctx:self.save(config)
        self.assertEqual(ctx.exception.code,403)
        with self.assertRaises(urllib.error.HTTPError):self.client.open(self.base+'/editor')
    def test_editor_changes_persist_and_invalid_input_rejected(self):
        self.login('editor');config=json.load(self.client.open(self.base+'/api/config'))
        config['title']='테스트 우리 집';config['theme_id']='forest';config['motion']['enabled']=False
        self.save(config)
        saved=json.loads((Path(self.tmp.name)/'panel.json').read_text())
        self.assertEqual(saved['title'],'테스트 우리 집');self.assertFalse(saved['motion']['enabled'])
        invalid=copy.deepcopy(config);invalid['theme']['accent']='red; background:url(https://evil)'
        with self.assertRaises(urllib.error.HTTPError) as ctx:self.save(invalid)
        self.assertEqual(ctx.exception.code,400)
        self.assertEqual(json.load(self.client.open(self.base+'/api/config'))['theme_id'],'forest')
    def test_cross_origin_write_and_bad_login_blocked(self):
        self.login('editor');config=json.load(self.client.open(self.base+'/api/config'))
        req=urllib.request.Request(self.base+'/api/config',method='PUT',data=json.dumps(config).encode(),headers={'Origin':'https://evil.invalid','Content-Type':'application/json'})
        with self.assertRaises(urllib.error.HTTPError) as ctx:self.client.open(req)
        self.assertEqual(ctx.exception.code,403)
        req=urllib.request.Request(self.base+'/api/login',data=b'{"role":"editor","password":"wrong"}',headers={'Origin':self.base,'Content-Type':'application/json'})
        with self.assertRaises(urllib.error.HTTPError) as ctx:self.client.open(req)
        self.assertEqual(ctx.exception.code,401)
    def test_malformed_login_payload_rejected(self):
        req=urllib.request.Request(self.base+'/api/login',data=b'[]',headers={'Origin':self.base,'Content-Type':'application/json'})
        with self.assertRaises(urllib.error.HTTPError) as ctx:self.client.open(req)
        self.assertEqual(ctx.exception.code,400)

    def test_routes_and_security_headers(self):
        self.login('viewer')
        for path in ['/../server.py','/data/options.json','/api/control']:
            with self.assertRaises(urllib.error.HTTPError) as ctx:self.client.open(self.base+path)
            self.assertEqual(ctx.exception.code,404)
        r=self.client.open(self.base+'/');self.assertIn("connect-src 'self'",r.headers['Content-Security-Policy'])
        self.assertEqual(json.load(self.client.open(self.base+'/health'))['ha_control'],False)

if __name__=='__main__':unittest.main()
