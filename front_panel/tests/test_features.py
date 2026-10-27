import copy,json,tempfile,threading,unittest,urllib.request,urllib.error
from pathlib import Path
import server

class FakeHA:
 def __init__(self):self.calls=[]
 def catalog(self):return []
 def states(self,ids):return {eid:{'entity_id':eid,'state':'off','name':eid,'unit':''} for eid in ids}
 def set_state(self,eid,state):self.calls.append((eid,state));return {'entity_id':eid,'state':state,'confirmed':True}

class FeaturesTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.ha=FakeHA();self.srv=server.create_server(('127.0.0.1',0),trusted_peers={'127.0.0.1'},viewer_ip='127.0.0.1',data_dir=Path(self.tmp.name),ha_client=self.ha)
  threading.Thread(target=self.srv.serve_forever,daemon=True).start();self.base=f'http://127.0.0.1:{self.srv.server_port}';self.headers={'X-Ingress-Path':'/api/hassio_ingress/test','Content-Type':'application/json','Origin':'https://ha.invalid'}
 def tearDown(self):self.srv.shutdown();self.srv.server_close();self.tmp.cleanup()
 def request(self,path,body=None,method=None):
  req=urllib.request.Request(self.base+path,headers=self.headers,data=None if body is None else json.dumps(body).encode(),method=method)
  return json.load(urllib.request.urlopen(req))
 def save_card(self,eid='switch.example',control=True):
  c=self.request('/api/config');card=c['rooms'][0]['cards'][0];card['entity_id']=eid;card['control']=control;self.request('/api/config',c,'PUT');return c['rooms'][0]['id'],card['id']
 def test_six_themes_and_dynamic_room_card(self):
  meta=self.request('/api/meta');self.assertEqual(len(meta['themes']),7)
  c=self.request('/api/config');c['theme_id']='forest';new=copy.deepcopy(c['rooms'][0]);new['id']='office';new['name']='서재';new['cards'].append({'id':'extra','label':'서재 스위치','icon':'power','entity_id':'switch.office','visible':True,'control':True});c['rooms'].append(new)
  self.request('/api/config',c,'PUT');saved=self.request('/api/config');self.assertEqual(saved['rooms'][-1]['name'],'서재');self.assertEqual(saved['rooms'][-1]['cards'][-1]['icon'],'power');self.assertEqual(saved['theme_id'],'forest')
 def test_selected_switch_control_and_state_readback(self):
  room,card=self.save_card();r=self.request('/api/control',{'room_id':room,'card_id':card,'state':'on'},'POST');self.assertTrue(r['confirmed']);self.assertEqual(self.ha.calls,[('switch.example','on')])
 def test_selected_automation_enable_disable(self):
  room,card=self.save_card('automation.example');r=self.request('/api/control',{'room_id':room,'card_id':card,'state':'off'},'POST');self.assertTrue(r['confirmed']);self.assertEqual(self.ha.calls,[('automation.example','off')])
 def test_readonly_automation_cannot_be_controlled(self):
  room,card=self.save_card('automation.example',False)
  with self.assertRaises(urllib.error.HTTPError):self.request('/api/control',{'room_id':room,'card_id':card,'state':'on'},'POST')
  self.assertEqual(self.ha.calls,[])
 def test_unselected_or_sensitive_domains_and_readonly_blocked(self):
  for eid,enabled in [('lock.front',True),('switch.example',False),('sensor.temperature',True)]:
   room,card=self.save_card(eid,enabled)
   with self.assertRaises(urllib.error.HTTPError):self.request('/api/control',{'room_id':room,'card_id':card,'state':'off'},'POST')
  self.assertEqual(self.ha.calls,[])
 def test_arbitrary_entity_and_toggle_payload_rejected(self):
  with self.assertRaises(urllib.error.HTTPError):self.request('/api/control',{'entity_id':'switch.not_selected','state':'on'},'POST')
  room,card=self.save_card()
  with self.assertRaises(urllib.error.HTTPError):self.request('/api/control',{'room_id':room,'card_id':card,'state':'toggle'},'POST')
  self.assertEqual(self.ha.calls,[])
 def test_v3_migration_preserves_bindings_and_labels(self):
  legacy=json.loads((Path(__file__).parent/'fixtures/legacy-v3.json').read_text());legacy['bindings']['rooms']['거실']['main']='light.example';legacy['cards'][0]['label']='내 조명'
  c=server.validate(legacy);self.assertEqual(c['rooms'][0]['cards'][0]['entity_id'],'light.example');self.assertEqual(c['rooms'][0]['cards'][0]['label'],'내 조명');self.assertTrue(c['rooms'][0]['cards'][0]['control'])
 def test_bad_icons_duplicate_rooms_rejected(self):
  c=copy.deepcopy(server.DEFAULT);c['rooms'][0]['cards'][0]['icon']='javascript:evil'
  with self.assertRaises(ValueError):server.validate(c)
  c=copy.deepcopy(server.DEFAULT);c['rooms'].append(copy.deepcopy(c['rooms'][0]))
  with self.assertRaises(ValueError):server.validate(c)
