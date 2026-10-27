import copy, unittest
from panel_config import DEFAULT, validate, selected_ids

class DynamicSensorsTest(unittest.TestCase):
 def test_custom_sensor_items_roundtrip_and_limits(self):
  c=copy.deepcopy(DEFAULT)
  items=[{'id':'custom-'+str(i),'label':'내 센서 '+str(i),'icon':'star','entity_id':'sensor.custom_'+str(i),'format':'auto'} for i in range(5)]
  c['rooms'][0]['sensors']=items
  saved=validate(c)
  self.assertEqual(saved['rooms'][0]['sensors'],items)
  self.assertEqual(selected_ids(saved),{x['entity_id'] for x in items})
  c['rooms'][0]['sensors']=[];self.assertEqual(validate(c)['rooms'][0]['sensors'],[])
  for bad in [items+[items[0]], [{**items[0],'icon':'invalid'}], [{**items[0],'entity_id':'../../secret'}], [{**items[0],'format':'invalid'}], [{**items[0],'control':True}], [dict(items[0],id='s'+str(i)) for i in range(17)]]:
   c['rooms'][0]['sensors']=bad
   with self.assertRaises(ValueError):validate(c)
