"""Password-free viewer IP + HA Ingress editor boundary."""
import copy,http.client,json,tempfile,threading,unittest
from pathlib import Path
import server

class FakeHA:
 def __init__(self):self.commands=[]
 def set_state(self,eid,state):self.commands.append((eid,state));return {'entity_id':eid,'state':state,'confirmed':True}

class PasswordFreeTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.ha=FakeHA();self.s=server.create_server(('127.0.0.1',0),trusted_peers={'127.0.0.3'},viewer_ip='127.0.0.1',data_dir=Path(self.tmp.name),ha_client=self.ha);self.t=threading.Thread(target=self.s.serve_forever,daemon=True);self.t.start();self.origin='http://127.0.0.1:'+str(self.s.server_port)
 def tearDown(self):self.s.shutdown();self.s.server_close();self.t.join();self.tmp.cleanup()
 def request(self,path,method='GET',data=None,peer='127.0.0.1',headers=None):
  h=dict(headers or {})
  if data is not None:h.update({'Content-Type':'application/json','Origin':self.origin})
  c=http.client.HTTPConnection('127.0.0.1',self.s.server_port,source_address=(peer,0));c.request(method,path,body=None if data is None else json.dumps(data),headers=h);r=c.getresponse();result=(r.status,dict(r.getheaders()),r.read());c.close();return result
 def test_exact_ip_is_viewer_without_password_or_cookie(self):
  for path in ['/','/api/config','/api/revision','/health']:
   status,headers,_=self.request(path);self.assertEqual(status,200);self.assertNotIn('Set-Cookie',headers)
 def test_ha_ingress_remains_the_only_editor(self):
  for path in ['/editor','/editor.js','/api/entities']:self.assertEqual(self.request(path)[0],403)
  for path,method in [('/api/config','PUT'),('/api/home-settings','POST')]:self.assertEqual(self.request(path,method,{})[0],403)
  h={'X-Ingress-Path':'/api/hassio_ingress/test'}
  self.assertEqual(self.request('/editor',peer='127.0.0.3',headers=h)[0],200)
  config=copy.deepcopy(server.DEFAULT);config['title']='Ingress only'
  self.assertEqual(self.request('/api/config','PUT',config,peer='127.0.0.3',headers=h)[0],200)
  self.assertEqual(json.loads(self.request('/api/config')[2])['title'],'Ingress only')
 def test_headers_and_old_cookies_cannot_elevate_viewer(self):
  h={'X-Ingress-Path':'/api/hassio_ingress/spoof','X-Forwarded-For':'127.0.0.3','X-Real-IP':'127.0.0.3','Cookie':'front_session=old-session'}
  self.assertEqual(self.request('/editor',headers=h)[0],403)
  self.assertEqual(self.request('/',peer='127.0.0.2',headers=h)[0],403)
 def test_login_endpoints_and_assets_are_gone(self):
  for p in ['/login','/login?role=editor','/login.js']:
   self.assertEqual(self.request(p)[0],404)
  for body in [{},[],{'role':'editor','password':'old-value'}]:self.assertEqual(self.request('/api/login','POST',body)[0],404)
  self.assertFalse((server.ROOT/'login.html').exists());self.assertFalse((server.ROOT/'login.js').exists())
 def test_blank_ip_fails_closed_but_ingress_still_works(self):
  app=server.create_server(('127.0.0.1',0),trusted_peers={'127.0.0.1'});t=threading.Thread(target=app.serve_forever,daemon=True);t.start()
  try:
   c=http.client.HTTPConnection('127.0.0.1',app.server_port);c.request('GET','/');r=c.getresponse();self.assertEqual(r.status,403);r.read();c.close()
   c=http.client.HTTPConnection('127.0.0.1',app.server_port);c.request('GET','/editor',headers={'X-Ingress-Path':'/api/hassio_ingress/test'});r=c.getresponse();self.assertEqual(r.status,200);r.read();c.close()
  finally:app.shutdown();app.server_close();t.join();app.temporary.cleanup()
 def test_viewer_can_only_control_registered_enabled_cards(self):
  config=copy.deepcopy(server.DEFAULT);card=config['rooms'][0]['cards'][0];card['entity_id']='light.fixture'
  h={'X-Ingress-Path':'/api/hassio_ingress/test'};self.assertEqual(self.request('/api/config','PUT',config,peer='127.0.0.3',headers=h)[0],200)
  command={'room_id':config['rooms'][0]['id'],'card_id':card['id'],'state':'on'}
  self.assertEqual(self.request('/api/control','POST',command)[0],200);self.assertEqual(self.ha.commands,[('light.fixture','on')])
  self.assertEqual(self.request('/api/control','POST',{**command,'card_id':'unregistered'})[0],403)
 def test_cross_origin_viewer_write_stays_rejected(self):
  c=http.client.HTTPConnection('127.0.0.1',self.s.server_port);c.request('POST','/api/appearance',body='{"color_mode":"light"}',headers={'Origin':'https://outside.invalid','Content-Type':'application/json'});r=c.getresponse();self.assertEqual(r.status,403);r.read();c.close()
 def test_options_and_implementation_have_no_password_auth(self):
  root=Path(__file__).resolve().parents[1];manifest=(root/'config.yaml').read_text();source=(root/'server.py').read_text()
  for token in ['viewer_password','editor_password']:self.assertNotIn(token,manifest);self.assertNotIn(token,source)
  for token in ['validate_passwords','pw_hash','scrypt','front_session','SimpleCookie']:self.assertNotIn(token,source)
  self.assertIn('version: "1.0.0"',manifest)

if __name__=='__main__':unittest.main()
