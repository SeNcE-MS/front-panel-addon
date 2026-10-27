import json,subprocess,unittest
from pathlib import Path
from panel_config import meta
class AddedIconsTest(unittest.TestCase):
 def test_curtain_and_blinds_have_named_svg_paths(self):
  icons={i['id']:i['name'] for i in meta()['icons']}
  self.assertEqual(icons.get('curtain'),'커튼');self.assertEqual(icons.get('blinds'),'블라인드');self.assertEqual(icons.get('led-strip'),'LED 스트립');self.assertEqual(icons.get('downlight'),'다운라이트')
  source=(Path(__file__).resolve().parents[1]/'www/ui.js').read_text()
  run=subprocess.run(['node','-e','global.window=global;'+source+';console.log(JSON.stringify([PanelIcons.curtain,PanelIcons.blinds,PanelIcons["led-strip"],PanelIcons.downlight]));'],capture_output=True,text=True)
  self.assertEqual(run.returncode,0,run.stderr)
  for path in json.loads(run.stdout):self.assertIsInstance(path,str);self.assertTrue(path.startswith('M'))
