import io,json,unittest
from unittest.mock import patch
from ha_bridge import HAClient,HAReadError

class HomeBridgeTest(unittest.TestCase):
 def test_todo_read_only_fixed_service_filter_cache_and_scope(self):
  calls=[]
  def network(req,timeout=None):
   calls.append(req)
   self.assertEqual(req.method,'POST')
   self.assertEqual(req.full_url,'http://test/api/services/todo/get_items?return_response')
   self.assertEqual(json.loads(req.data),{'entity_id':'todo.test','status':'needs_action'})
   return io.BytesIO(json.dumps({'changed_states':[],'service_response':{'todo.test':{'items':[{'summary':'진행중','status':'needs_action'},{'summary':'완료','status':'completed'}]}}}).encode())
  client=HAClient('test-token','http://test/api')
  with patch('ha_bridge.urlopen',network):
   self.assertEqual(client.todo_items('todo.test'),[{'summary':'진행중','due':''}]);client.todo_items('todo.test')
   with self.assertRaises(HAReadError):client.todo_items('switch.test')
  self.assertEqual(len(calls),1)
 def test_weather_and_timestamp_metadata_are_slim_and_safe(self):
  weather=HAClient.slim({'entity_id':'weather.test','state':'rainy','attributes':{'temperature':20,'humidity':80,'secret':'never','temperature_unit':'°C'}})
  self.assertEqual(weather['attributes'],{'temperature':20,'humidity':80,'temperature_unit':'°C'})
  self.assertEqual(HAClient.slim({'entity_id':'sensor.end','state':'unknown','attributes':{'device_class':'timestamp'}})['attributes']['device_class'],'timestamp')
