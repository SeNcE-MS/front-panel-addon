import json,tempfile,threading,unittest,urllib.request,urllib.error
from pathlib import Path
import server
class AutoViewerTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.srv=server.create_server(('127.0.0.1',0),trusted_peers=set(),viewer_ip='127.0.0.1',data_dir=Path(self.tmp.name));threading.Thread(target=self.srv.serve_forever,daemon=True).start();self.base=f'http://127.0.0.1:{self.srv.server_port}'
 def tearDown(self):self.srv.shutdown();self.srv.server_close();self.tmp.cleanup()
 def call(self,path,method='GET',body=None,origin=None):
  h={}
  if body is not None:h['Content-Type']='application/json'
  if origin is not None:h['Origin']=origin
  req=urllib.request.Request(self.base+path,data=None if body is None else json.dumps(body).encode(),headers=h,method=method)
  try:
   with urllib.request.urlopen(req) as response:return response.status,response.geturl()
  except urllib.error.HTTPError as error:return error.code,error.geturl()
 def test_ip_viewer_without_login_redirect(self):
  self.assertEqual(self.call('/')[0],200);self.assertEqual(self.call('/api/config')[0],200);self.assertEqual(self.call('/login')[0],404);self.assertEqual(self.call('/login?role=editor')[0],404)
 def test_editor_stays_protected(self):
  for path in ['/editor','/editor.js','/api/entities']:self.assertEqual(self.call(path)[0],403)
  for path,method in [('/api/config','PUT'),('/api/home-settings','POST')]:self.assertEqual(self.call(path,method,{},self.base)[0],403)
  self.assertEqual(self.call('/api/login','POST',{'role':'editor'},self.base)[0],404)
 def test_cross_origin_and_public_peer_still_rejected(self):
  self.assertEqual(self.call('/api/appearance','POST',{'color_mode':'light'},'https://outside.invalid')[0],403)
  handler=object.__new__(self.srv.RequestHandlerClass);handler.client_address=('203.0.113.1',123);handler.headers={};self.assertIsNone(handler._role());self.assertFalse(handler._peer_allowed())
 def test_no_password_validation_or_cookie_session_implementation(self):
  self.assertFalse(hasattr(server,'validate_passwords'));self.assertNotIn('/login',server.ROUTES)
