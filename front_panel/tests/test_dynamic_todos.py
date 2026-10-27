import copy,unittest
from home_config import HOME_DEFAULT,validate_home
class DynamicTodosTest(unittest.TestCase):
 def test_accepts_variable_lists_without_fixed_personal_names(self):
  for count in [0,1,5,16]:
   h=copy.deepcopy(HOME_DEFAULT);h['todos']['lists']=[{'label':'', 'entity_id':f'todo.list_{i}'} for i in range(count)]
   self.assertEqual(validate_home(h),h)
 def test_preserves_legacy_labels_and_bindings(self):
  h=copy.deepcopy(HOME_DEFAULT);h['todos']['lists']=[{'label':name,'entity_id':f'todo.old_{i}'} for i,name in enumerate(['일정','다이소','마트','쿠팡'])]
  self.assertEqual(validate_home(h),h)
 def test_rejects_wrong_domains_and_oversized_lists(self):
  for items in [[{'label':'','entity_id':'light.wrong'}],[{'label':'','entity_id':''}]*17,[{'label':'x'*161,'entity_id':''}]]:
   h=copy.deepcopy(HOME_DEFAULT);h['todos']['lists']=items
   with self.assertRaises(ValueError):validate_home(h)
 def test_generic_defaults(self):
  self.assertFalse(any(x['label'] in ['일정','다이소','마트','쿠팡'] for x in HOME_DEFAULT['todos']['lists']))
