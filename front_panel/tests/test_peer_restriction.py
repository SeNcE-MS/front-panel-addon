import http.client,tempfile,threading,unittest
from pathlib import Path
import server
class PeerRestrictionTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.s=server.create_server(('127.0.0.1',0),trusted_peers={'127.0.0.3'},data_dir=Path(self.tmp.name),viewer_ip='127.0.0.1');threading.Thread(target=self.s.serve_forever,daemon=True).start()
 def tearDown(self):self.s.shutdown();self.s.server_close();self.tmp.cleanup()
 def request(self,path='/',peer='127.0.0.1',method='GET',headers=None):
  c=http.client.HTTPConnection('127.0.0.1',self.s.server_port,source_address=(peer,0));c.request(method,path,headers=headers or {});r=c.getresponse();status=r.status;r.read();c.close();return status
 def test_allowed_viewer_without_login(self):
  for p in ['/','/api/config','/api/revision']:self.assertEqual(self.request(p),200)
  self.assertEqual(self.request('/editor'),403)
 def test_other_peer_blocked_on_all_routes(self):
  for method,p in [('GET','/'),('GET','/health'),('GET','/api/config'),('GET','/login'),('GET','/app.js'),('POST','/api/login'),('POST','/api/control'),('PUT','/api/config')]:self.assertEqual(self.request(p,'127.0.0.2',method),403)
 def test_spoofed_headers_cannot_bypass(self):
  self.assertEqual(self.request('/','127.0.0.2',headers={'X-Forwarded-For':'127.0.0.1','X-Real-IP':'127.0.0.1','X-Ingress-Path':'/api/hassio_ingress/fake'}),403)
  self.assertEqual(self.request('/','127.0.0.3'),403)
 def test_authenticated_ingress_editor_preserved(self):
  h={'X-Ingress-Path':'/api/hassio_ingress/testtoken'}
  self.assertEqual(self.request('/editor','127.0.0.3',headers=h),200)
  self.assertEqual(self.request('/api/config','127.0.0.3',headers=h),200)
 def test_user_ip_exact_matching(self):
  other=server.create_server(('127.0.0.1',0),data_dir=Path(self.tmp.name)/'other',viewer_ip='192.168.1.50')
  try:
   obj=object.__new__(other.RequestHandlerClass);obj.headers={};obj.client_address=('192.168.1.50',123);self.assertTrue(obj._peer_allowed());obj.client_address=('192.168.1.51',123);self.assertFalse(obj._peer_allowed())
  finally:other.server_close()
 def test_invalid_restriction_is_rejected(self):
  for ip in ['192.168.0.0/24',' 192.168.1.50','0.0.0.0','8.8.8.8',None]:
   with self.assertRaises(ValueError):server.validate_viewer_ip(ip)
