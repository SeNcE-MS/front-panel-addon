import http.cookiejar,json,tempfile,threading,unittest,urllib.request,urllib.error
from pathlib import Path
import server
class AutoViewerTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();p=server.validate_passwords({'viewer':'','editor':'editor-test-password'});self.srv=server.create_server(('127.0.0.1',0),trusted_peers=set(),data_dir=Path(self.tmp.name),passwords=p);threading.Thread(target=self.srv.serve_forever,daemon=True).start();self.base=f'http://127.0.0.1:{self.srv.server_port}';self.op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
 def tearDown(self):self.srv.shutdown();self.srv.server_close();self.tmp.cleanup()
 def call(self,path,method='GET',body=None,origin=None):
  headers={}
  if body is not None:headers['Content-Type']='application/json'
  if origin is not None:headers['Origin']=origin
  req=urllib.request.Request(self.base+path,data=None if body is None else json.dumps(body).encode(),headers=headers,method=method)
  try:
   with self.op.open(req) as response:return response.status,response.geturl()
  except urllib.error.HTTPError as e:return e.code,e.geturl()
 def test_auto_viewer_and_login_page_redirect(self):
  self.assertEqual(self.call('/')[0],200);self.assertEqual(self.call('/api/config')[0],200);self.assertEqual(self.call('/login')[1],self.base+'/');self.assertTrue(self.call('/login?role=editor')[1].endswith('?role=editor'))
 def test_editor_stays_protected(self):
  for path in ['/editor','/editor.js','/api/entities']:self.assertEqual(self.call(path)[0],403)
  for path,method in [('/api/config','PUT'),('/api/home-settings','POST')]:self.assertEqual(self.call(path,method,{},self.base)[0],403)
  self.assertEqual(self.call('/api/login','POST',{'role':'editor','password':''},self.base)[0],401)
  self.assertEqual(self.call('/api/login','POST',{'role':'editor','password':'editor-test-password'},self.base)[0],200);self.assertEqual(self.call('/editor')[0],200)
 def test_cross_origin_and_public_peer_still_rejected(self):
  self.assertEqual(self.call('/api/appearance','POST',{'color_mode':'light'},'https://outside.invalid')[0],403)
  handler=object.__new__(self.srv.RequestHandlerClass);handler.client_address=('203.0.113.1',123);handler.headers={};self.assertIsNone(handler._role())
 def test_only_editor_hash_registered(self):
  self.assertEqual(server.validate_passwords({'viewer':'','editor':'editor-test-password'}),{'editor':'editor-test-password'})
  with self.assertRaises(ValueError):server.validate_passwords({'viewer':'','editor':'short'})
