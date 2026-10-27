import copy,unittest
from home_config import HOME_DEFAULT,validate_home,home_ids
class PrecipitationBinding(unittest.TestCase):
 def test_legacy_migrates_empty_and_keeps_original(self):
  old=copy.deepcopy(HOME_DEFAULT);old['weather']['sensors'].pop('precipitation_probability',None);before=copy.deepcopy(old)
  c=validate_home(old);self.assertEqual(c['weather']['sensors']['precipitation_probability'],'');self.assertEqual(old,before)
 def test_saved_sensor_is_selected_and_scope_validated(self):
  c=copy.deepcopy(HOME_DEFAULT);c['enabled']=True;c['weather']['sensors']['precipitation_probability']='sensor.fixture_rain';self.assertIn('sensor.fixture_rain',home_ids(validate_home(c)))
  c['weather']['sensors']['precipitation_probability']='switch.invalid'
  with self.assertRaises(ValueError):validate_home(c)
