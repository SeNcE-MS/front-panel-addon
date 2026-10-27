import io,json,unittest
from unittest.mock import patch
from urllib.error import URLError
from ha_bridge import HAClient,HAReadError

class HAServiceBridgeTest(unittest.TestCase):
 def test_automation_enable_disable_never_triggers_or_stops_running_actions(self):
  for desired in ['on','off']:
   calls=[];current='off' if desired=='on' else 'on'
   def network(req,timeout=None):
    nonlocal current
    calls.append(req)
    if req.method=='POST':
     self.assertEqual(req.full_url,'http://test/api/services/automation/turn_'+desired)
     self.assertEqual(json.loads(req.data),{'entity_id':'automation.test',**({'stop_actions':False} if desired=='off' else {})})
     current=desired;return io.BytesIO(b'[]')
    return io.BytesIO(json.dumps({'entity_id':'automation.test','state':current,'attributes':{}}).encode())
   with patch('ha_bridge.urlopen',network):result=HAClient('test-only-token','http://test/api').set_state('automation.test',desired)
   self.assertTrue(result['confirmed']);self.assertFalse(any('/trigger' in req.full_url for req in calls))
 def test_automation_trigger_is_not_supported(self):
  with patch('ha_bridge.urlopen') as network:
   with self.assertRaises(HAReadError):HAClient('test-only-token').set_state('automation.test','trigger')
   network.assert_not_called()
 def test_service_is_scoped_post_and_readback_confirms(self):
  calls=[];current='off'
  def open_request(req,timeout=None):
   nonlocal current
   calls.append((req.method,req.full_url,req.data))
   if req.method=='POST':
    self.assertEqual(req.full_url,'http://test/api/services/switch/turn_on');self.assertEqual(json.loads(req.data),{'entity_id':'switch.test'});current='on';return io.BytesIO(b'[]')
   return io.BytesIO(json.dumps({'entity_id':'switch.test','state':current,'attributes':{}}).encode())
  with patch('ha_bridge.urlopen',open_request):result=HAClient('test-only-token','http://test/api').set_state('switch.test','on')
  self.assertTrue(result['confirmed']);self.assertEqual(result['state'],'on');self.assertEqual([x[0] for x in calls],['GET','POST','GET'])
 def test_sensitive_domains_never_call_service(self):
  with patch('ha_bridge.urlopen') as network:
   for eid in ['lock.front','cover.garage','climate.home','sensor.temp']:
    with self.assertRaises(HAReadError):HAClient('test-only-token').set_state(eid,'off')
   network.assert_not_called()
 def test_unavailable_never_posts(self):
  def read(req,timeout=None):self.assertEqual(req.method,'GET');return io.BytesIO(b'{"entity_id":"switch.test","state":"unavailable","attributes":{}}')
  with patch('ha_bridge.urlopen',read):
   with self.assertRaises(HAReadError):HAClient('test-only-token').set_state('switch.test','on')
 def test_uncertain_post_not_retried(self):
  posts=[]
  def network(req,timeout=None):
   if req.method=='POST':posts.append(req);raise URLError('test timeout')
   return io.BytesIO(b'{"entity_id":"switch.test","state":"off","attributes":{}}')
  with patch('ha_bridge.urlopen',network):
   with self.assertRaisesRegex(HAReadError,'불확실'):HAClient('test-only-token').set_state('switch.test','on')
  self.assertEqual(len(posts),1)
