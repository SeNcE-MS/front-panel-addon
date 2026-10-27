import copy,unittest
from home_config import HOME_DEFAULT,validate_home,home_ids
class WeatherPrecision(unittest.TestCase):
 def test_legacy_precision_and_humidity_migrate_without_mutation(self):
  old=copy.deepcopy(HOME_DEFAULT);old['weather'].pop('temperature_decimals',None);old['weather']['sensors'].pop('humidity',None);original=copy.deepcopy(old)
  c=validate_home(old);self.assertEqual(c['weather']['temperature_decimals'],1);self.assertEqual(c['weather']['sensors']['humidity'],'');self.assertEqual(old,original)
 def test_precision_scope_and_humidity_selection(self):
  for precision in [0,1]:
   c=copy.deepcopy(HOME_DEFAULT);c['enabled']=True;c['weather']['temperature_decimals']=precision;c['weather']['sensors']['humidity']='sensor.humidity';self.assertIn('sensor.humidity',home_ids(validate_home(c)))
  for bad in [True,False,2,-1,'1',None]:
   c=copy.deepcopy(HOME_DEFAULT);c['weather']['temperature_decimals']=bad
   with self.assertRaises(ValueError):validate_home(c)
 def test_show_humidity_migrates_true_and_is_strict_bool(self):
  c=copy.deepcopy(HOME_DEFAULT);c['weather'].pop('show_humidity',None)
  self.assertIs(validate_home(c)['weather']['show_humidity'],True)
  for value in [True,False]:
   c['weather']['show_humidity']=value;self.assertIs(validate_home(c)['weather']['show_humidity'],value)
  for value in [0,1,None,'false']:
   c['weather']['show_humidity']=value
   with self.assertRaises(ValueError):validate_home(c)
