import unittest
from pathlib import Path
from theme_palettes import preset

class ReferenceGlassTests(unittest.TestCase):
 def test_reference_material_is_neutral_grey_not_blue(self):
  for mode in ['light','dark']:
   palette=preset('glass',mode)
   for key in ['background','surface','text','muted','accent','soft','iconBgOn','iconOn']:
    rgb=[int(palette[key][i:i+2],16) for i in [1,3,5]]
    self.assertLessEqual(max(rgb)-min(rgb),12,(mode,key,palette[key]))
   self.assertEqual(palette['active'],'#ffffff')
   self.assertEqual(palette['onActive'],'#242629')
 def test_grey_material_has_static_edge_and_surface_depth(self):
  css=(Path(__file__).parents[1]/'www/glass.css').read_text()
  self.assertIn('--glass-reflection:',css)
  self.assertIn('background-image:var(--glass-reflection)',css)
  self.assertIn('border-top-color:var(--glass-rim)',css)
  self.assertIn('backdrop-filter:none!important',css)
  for old_blue in ['#283443','#1b2532','#141e29','#c7dce9','#eaf3fc','#253549']:
   self.assertNotIn(old_blue,css)

 def test_palette_upgrade_backs_up_current_settings_before_normalizing(self):
  import copy,json,tempfile
  import server
  from panel_config import DEFAULT,validate
  with tempfile.TemporaryDirectory() as tmp:
   raw=validate(copy.deepcopy(DEFAULT));raw['theme_id']='glass';raw['theme']['accent']='#9ec7ff'
   root=Path(tmp);(root/'panel.json').write_text(json.dumps(raw))
   srv=server.create_server(('127.0.0.1',0),data_dir=root)
   try:
    self.assertTrue((root/'panel.pre-v828.json').exists())
    self.assertEqual(json.loads((root/'panel.pre-v828.json').read_text()),raw)
    normalized=json.loads((root/'panel.json').read_text())
    self.assertEqual(normalized['rooms'],raw['rooms'])
    self.assertEqual(normalized['theme']['accent'],preset('glass','dark')['accent'])
   finally:srv.server_close()

if __name__=='__main__':unittest.main()
