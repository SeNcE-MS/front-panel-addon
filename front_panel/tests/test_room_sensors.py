import copy,json,unittest
from pathlib import Path
from panel_config import DEFAULT,validate,selected_ids,meta
class RoomSensorThemeTest(unittest.TestCase):
 def test_sensors_are_per_room_and_selected_ids_includes_each(self):
  c=copy.deepcopy(DEFAULT);self.assertNotIn('sensors',c)
  c['rooms'][0]['sensors']['temperature']='sensor.living_temperature';c['rooms'][1]['sensors']['temperature']='sensor.bedroom_temperature';c['rooms'][1]['sensors']['window']='binary_sensor.bedroom_window'
  saved=validate(c);self.assertNotEqual(saved['rooms'][0]['sensors'],saved['rooms'][1]['sensors']);self.assertEqual(selected_ids(saved),{'sensor.living_temperature','sensor.bedroom_temperature','binary_sensor.bedroom_window'})
 def test_v4_shared_sensors_migrate_to_first_room_only(self):
  old=json.loads((Path(__file__).parent/'fixtures/legacy-v4.json').read_text());saved=validate(old)
  self.assertEqual({s['id']:s['entity_id'] for s in saved['rooms'][0]['sensors']},old['sensors']);self.assertNotIn('sensors',saved)
  for room in saved['rooms'][1:]:self.assertFalse(any(s['entity_id'] for s in room['sensors']))
  self.assertEqual(saved['rooms'][0]['cards'],old['rooms'][0]['cards'])
 def test_new_room_sensors_default_to_empty_and_invalid_ids_rejected(self):
  c=copy.deepcopy(DEFAULT);c['rooms'].append({'id':'test-room','name':'서재','cards':[]});self.assertEqual({s['id']:s['entity_id'] for s in validate(c)['rooms'][-1]['sensors']},{'temperature':'','humidity':'','window':''})
  c=validate(c);c['rooms'][-1]['sensors'][2]['entity_id']='../../secret'
  with self.assertRaises(ValueError):validate(c)
 def test_six_complete_presets_and_accessible_text(self):
  themes=meta()['themes'];self.assertEqual(len(themes),7)
  def luminance(hex):
   rgb=[int(hex[i:i+2],16)/255 for i in (1,3,5)];linear=[x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in rgb];return sum(a*b for a,b in zip(linear,[.2126,.7152,.0722]))
  def contrast(a,b):a,b=sorted([luminance(a),luminance(b)]);return (b+.05)/(a+.05)
  for theme in themes:
   for mode in ['light','dark']:
    c=copy.deepcopy(DEFAULT);c['theme_id']=theme['id'];c['color_mode']=mode;t=validate(c)['theme']
    self.assertEqual(t['mode'],mode);self.assertEqual(t['switchOn'],'#288955' if theme['id']=='glass' else t['accent'])
    for fg,bg in [('text','background'),('muted','surface'),('muted','background'),('onAccent','accent'),('onActive','active'),('iconOn','iconBgOn')]:self.assertGreaterEqual(contrast(t[fg],t[bg]),4.5,(theme['id'],mode,fg,bg))
  c=copy.deepcopy(DEFAULT);c['theme_id']='ember';c['color_mode']='light';self.assertEqual(validate(c)['theme']['mode'],'light')
 def test_editor_does_not_use_native_datalist(self):
  root=Path(__file__).resolve().parents[1]/'www';html=(root/'editor.html').read_text();script=(root/'editor.js').read_text()
  self.assertNotIn('<datalist',html);self.assertNotIn("setAttribute('list'",script);self.assertIn('visualViewport',script)
