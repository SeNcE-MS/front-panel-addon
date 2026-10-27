import copy,unittest
from home_config import HOME_DEFAULT,validate_home,home_ids
class HomeIconAnimationTest(unittest.TestCase):
 def test_legacy_home_migrates_without_changing_bindings(self):
  legacy=copy.deepcopy(HOME_DEFAULT);legacy.pop('icon_animation',None);saved=validate_home(legacy);self.assertIs(saved.pop('icon_animation'),True);self.assertEqual(saved,legacy)
 def test_off_persists_and_does_not_change_entity_scope(self):
  home=copy.deepcopy(HOME_DEFAULT);before=home_ids(home);home['icon_animation']=False;saved=validate_home(home);self.assertIs(saved['icon_animation'],False);self.assertEqual(home_ids(saved),before)
 def test_strict_bool(self):
  for bad in [0,1,'true',None]:
   home=copy.deepcopy(HOME_DEFAULT);home['icon_animation']=bad
   with self.assertRaises(ValueError):validate_home(home)
