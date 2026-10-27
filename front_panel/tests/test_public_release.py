"""Public release metadata/documentation must agree without altering bindings."""
from pathlib import Path
from threading import Thread
from urllib.request import urlopen
import json,unittest
import server
from panel_config import DEFAULT,validate,selected_ids

ROOT=Path(__file__).resolve().parents[1]
REPO='https://github.com/SeNcE-MS/front-panel-addon'

class ReleaseTests(unittest.TestCase):
 def test_version_is_one_in_manifest_health_and_startup(self):
  self.assertIn('version: "1.0.0"',(ROOT/'config.yaml').read_text())
  self.assertIn('Front Panel 1.0.0;', (ROOT/'server.py').read_text())
  app=server.create_server(('127.0.0.1',0),viewer_ip='127.0.0.1');thread=Thread(target=app.serve_forever,daemon=True);thread.start()
  try:
   with urlopen('http://127.0.0.1:'+str(app.server_port)+'/health') as response:
    self.assertEqual(json.load(response)['version'],'1.0.0')
  finally:
   app.shutdown();app.server_close();thread.join();app.temporary.cleanup()
 def test_docs_are_installation_instructions_without_development_history(self):
  text=(ROOT/'DOCS.md').read_text()
  for needed in ['# Front Panel 1.0.0',REPO,'## 설치 방법','viewer_ip','## 사용 안내','## 참고']:
   self.assertIn(needed,text)
  for old in ['0.8.','이전 기능 기록','변경 사항']:
   self.assertNotIn(old,text)
  self.assertIn('url: '+REPO,(ROOT/'config.yaml').read_text())
 def test_default_configuration_has_no_household_entity_bindings(self):
  self.assertEqual(selected_ids(validate(DEFAULT)),set())

if __name__=='__main__':unittest.main()
