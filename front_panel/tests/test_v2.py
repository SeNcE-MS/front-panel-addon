import copy,json,tempfile,threading,unittest,urllib.request,urllib.error
from pathlib import Path
import server

class DirectPanelTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.srv=server.create_server(('127.0.0.1',0),trusted_peers={'127.0.0.1'},viewer_ip='127.0.0.1',data_dir=Path(self.tmp.name));threading.Thread(target=self.srv.serve_forever,daemon=True).start();self.base=f'http://127.0.0.1:{self.srv.server_port}';self.client=urllib.request.build_opener()
 def tearDown(self):self.srv.shutdown();self.srv.server_close();self.tmp.cleanup()
 def ingress(self):self.client.addheaders=[('X-Ingress-Path','/api/hassio_ingress/test')]
 def save(self,config,origin=None):return self.client.open(urllib.request.Request(self.base+'/api/config',method='PUT',data=json.dumps(config).encode(),headers={'Content-Type':'application/json','Origin':origin or self.base}))
 def test_allowed_viewer_direct_access_and_editor_isolation(self):
  html=self.client.open(self.base+'/').read().decode();self.assertIn('app.js',html);self.assertNotIn('editor.js',html);config=json.load(self.client.open(self.base+'/api/config'))
  with self.assertRaises(urllib.error.HTTPError) as ctx:self.save(config)
  self.assertEqual(ctx.exception.code,403)
  for path in ['/editor','/editor.js','/api/entities']:
   with self.assertRaises(urllib.error.HTTPError) as ctx:self.client.open(self.base+path)
   self.assertEqual(ctx.exception.code,403)
 def test_editor_changes_persist_and_invalid_input_rejected(self):
  self.ingress();config=json.load(self.client.open(self.base+'/api/config'));config['title']='테스트 우리 집';config['theme_id']='forest';config['motion']['enabled']=False;self.save(config);saved=json.loads((Path(self.tmp.name)/'panel.json').read_text());self.assertEqual(saved['title'],'테스트 우리 집');self.assertFalse(saved['motion']['enabled']);invalid=copy.deepcopy(config);invalid['theme']['accent']='red; background:url(https://evil)'
  with self.assertRaises(urllib.error.HTTPError) as ctx:self.save(invalid)
  self.assertEqual(ctx.exception.code,400);self.assertEqual(json.load(self.client.open(self.base+'/api/config'))['theme_id'],'forest')
 def test_cross_origin_viewer_write_blocked(self):
  req=urllib.request.Request(self.base+'/api/appearance',method='POST',data=b'{"color_mode":"light"}',headers={'Origin':'https://outside.invalid','Content-Type':'application/json'})
  with self.assertRaises(urllib.error.HTTPError) as ctx:self.client.open(req)
  self.assertEqual(ctx.exception.code,403)
 def test_removed_login_endpoint_never_accepts_payload(self):
  for body in [b'[]',b'{}',b'{"role":"editor","password":"old"}']:
   req=urllib.request.Request(self.base+'/api/login',data=body,headers={'Origin':self.base,'Content-Type':'application/json'})
   with self.assertRaises(urllib.error.HTTPError) as ctx:self.client.open(req)
   self.assertEqual(ctx.exception.code,404)
 def test_viewer_appearance_only_write_preserves_bindings(self):
  before=json.load(self.client.open(self.base+'/api/config'));req=urllib.request.Request(self.base+'/api/appearance',method='POST',data=b'{"color_mode":"light"}',headers={'Origin':self.base,'Content-Type':'application/json'});self.assertEqual(json.load(self.client.open(req))['config']['color_mode'],'light');after=json.load(self.client.open(self.base+'/api/config'));self.assertEqual(before['rooms'],after['rooms'])
 def test_routes_and_security_headers(self):
  for path in ['/../server.py','/data/options.json','/api/control']:
   with self.assertRaises(urllib.error.HTTPError) as ctx:self.client.open(self.base+path)
   self.assertEqual(ctx.exception.code,404)
  r=self.client.open(self.base+'/');self.assertIn("connect-src 'self'",r.headers['Content-Security-Policy']);self.assertNotIn('Set-Cookie',r.headers);self.assertEqual(json.load(self.client.open(self.base+'/health'))['ha_control'],False)

if __name__=='__main__':unittest.main()
