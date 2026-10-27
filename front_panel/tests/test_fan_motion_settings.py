import copy,unittest
from panel_config import DEFAULT,validate,selected_ids
class FanMotionSettingsTest(unittest.TestCase):
 def test_legacy_defaults_on_and_preserves_everything_else(self):
  raw=validate(copy.deepcopy(DEFAULT));raw['motion'].pop('fan_enabled',None);before=copy.deepcopy(raw);out=validate(raw);self.assertIs(out['motion'].pop('fan_enabled',None),True);self.assertEqual(out,before);self.assertEqual(raw,before)
 def test_off_persists_without_changing_scope(self):
  raw=validate(copy.deepcopy(DEFAULT));before=selected_ids(raw);raw['motion']['fan_enabled']=False;out=validate(raw);self.assertIs(out['motion']['fan_enabled'],False);self.assertEqual(selected_ids(out),before)
 def test_only_strict_bool(self):
  for bad in [0,1,'true',None]:
   raw=copy.deepcopy(DEFAULT);raw['motion']['fan_enabled']=bad
   with self.assertRaises(ValueError):validate(raw)
