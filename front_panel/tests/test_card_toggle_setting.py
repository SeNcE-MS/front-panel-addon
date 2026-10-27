import copy,unittest
from panel_config import DEFAULT,validate
class CardToggleSettings(unittest.TestCase):
 def test_migration_defaults_visible_without_mutating_source(self):
  old=copy.deepcopy(DEFAULT);old['display'].pop('card_toggles',None);before=copy.deepcopy(old)
  self.assertIs(validate(old)['display']['card_toggles'],True);self.assertEqual(old,before)
 def test_strict_boolean_and_other_settings_preserved(self):
  for value in [True,False]:
   old=validate(DEFAULT);old['display']['card_toggles']=value;self.assertEqual(validate(old),old)
  for bad in ['false',0,1,None]:
   old=copy.deepcopy(DEFAULT);old['display']['card_toggles']=bad
   with self.assertRaises(ValueError):validate(old)
