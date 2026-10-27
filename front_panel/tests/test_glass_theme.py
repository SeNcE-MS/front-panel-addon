import copy,json,unittest
from pathlib import Path
from panel_config import DEFAULT,meta,validate
from theme_palettes import preset

class GlassThemeTests(unittest.TestCase):
 def test_glass_is_additional_independent_light_dark_theme(self):
  themes=meta()['themes'];by_id={t['id']:t for t in themes}
  self.assertIn('glass',by_id)
  self.assertEqual([t['id'] for t in themes],['navy','ocean','forest','plum','ember','slate','glass'])
  self.assertEqual(by_id['glass']['name'],'글라스')
  baseline=json.loads((Path(__file__).parent/'fixtures/themes-pre-glass.json').read_text())
  for key,modes in baseline.items():
   for mode,colors in modes.items():self.assertEqual(preset(key,mode),colors)
  for mode in ['light','dark']:
   raw=copy.deepcopy(DEFAULT);raw['theme_id']='glass';raw['color_mode']=mode
   before=copy.deepcopy(raw);c=validate(raw)
   self.assertEqual(raw,before)
   self.assertEqual(c['theme']['mode'],mode)
   self.assertEqual(c['theme']['active'],'#ffffff')
   self.assertEqual(c['theme']['onActive'],'#242629')
   for key in ['rooms','home','display','motion','title','brand','subtitle']:self.assertEqual(c[key],validate(before)[key])
if __name__=='__main__':unittest.main()
