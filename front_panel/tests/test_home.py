import copy,unittest
from panel_config import DEFAULT,validate,selected_ids

class HomeConfigTest(unittest.TestCase):
 def test_home_settings_migrate_independently_and_validate_scope(self):
  original=copy.deepcopy(DEFAULT);c=validate(original)
  self.assertIn('home',c)
  h=c['home'];self.assertFalse(h['enabled']);self.assertFalse(h['auto_return'])
  h['enabled']=True;h['auto_return']=True
  h['weather'].update(enabled=True,entity_id='weather.test')
  h['washer'].update(enabled=True,state_entity='sensor.washer',remaining_entity='sensor.remaining')
  h['todos']['enabled']=True;h['todos']['lists'][0]['entity_id']='todo.test'
  saved=validate(c);self.assertEqual(saved,c);self.assertEqual(original,DEFAULT)
  self.assertTrue({'weather.test','sensor.washer','sensor.remaining','todo.test'}<=selected_ids(saved))
  for key,value in [('enabled',1),('auto_return','true')]:
   bad=copy.deepcopy(c);bad['home'][key]=value
   with self.assertRaises(ValueError):validate(bad)
  bad=copy.deepcopy(c);bad['home']['weather']['entity_id']='lock.front'
  with self.assertRaises(ValueError):validate(bad)
  bad=copy.deepcopy(c);bad['home']['todos']['lists'][0]['entity_id']='switch.test'
  with self.assertRaises(ValueError):validate(bad)
  h['enabled']=False
  self.assertNotIn('weather.test',selected_ids(validate(c)))
