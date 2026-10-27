import copy,unittest
from home_config import HOME_DEFAULT,validate_home,home_ids
class WeatherDetailsTest(unittest.TestCase):
 def test_weather_detail_sensor_scope_and_legacy_migration(self):
  old=copy.deepcopy(HOME_DEFAULT);old['weather'].pop('sensors',None)
  c=validate_home(old);self.assertIn('sensors',c['weather']);self.assertEqual(len(c['weather']['sensors']),10)
  c['enabled']=True;c['weather']['sensors']['wind']='sensor.wind';c['weather']['sensors']['high']='sensor.high';self.assertTrue({'sensor.wind','sensor.high'}<=home_ids(c))
  for bad in ['switch.fan','../../secret']:
   broken=copy.deepcopy(c);broken['weather']['sensors']['wind']=bad
   with self.assertRaises(ValueError):validate_home(broken)
  c['weather']['enabled']=False;self.assertNotIn('sensor.wind',home_ids(c))
