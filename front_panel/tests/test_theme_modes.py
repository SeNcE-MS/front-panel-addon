import copy,json,tempfile,threading,unittest,urllib.request,urllib.error
from pathlib import Path
import server
from panel_config import DEFAULT,meta,preset,validate
class ThemeModesTest(unittest.TestCase):
 def test_six_colors_times_two_modes_and_independence(self):
  themes=meta()['themes'];self.assertEqual(len(themes),7);self.assertEqual(sum(len(t['modes']) for t in themes),14)
  for theme in themes:
   for mode in ['light','dark']:
    c=copy.deepcopy(DEFAULT);c['theme_id']=theme['id'];c['color_mode']=mode;c=validate(c)
    self.assertEqual(c['color_mode'],mode);self.assertEqual(c['theme']['mode'],mode);self.assertEqual(c['theme'],{**c['theme'],**preset(theme['id'],mode)})
    self.assertNotEqual(theme['modes']['light']['background'],theme['modes']['dark']['background'])
 def test_v5_preserves_rooms_and_prior_mode(self):
  old=json.loads((Path(__file__).parent/'fixtures/legacy-v5.json').read_text());c=validate(old)
  self.assertEqual([{**r,'sensors':{s['id']:s['entity_id'] for s in r['sensors']}} for r in c['rooms']],old['rooms']);self.assertEqual(c['theme_id'],old['theme_id']);self.assertEqual(c['color_mode'],old['theme']['mode'])
 def test_invalid_mode_rejected(self):
  for mode in ['auto','bright',True,[],None]:
   c=copy.deepcopy(DEFAULT);c['color_mode']=mode
   with self.assertRaises(ValueError):validate(c)
 def test_viewer_mode_toggle_does_not_overwrite_rooms(self):
  with tempfile.TemporaryDirectory() as tmp:
   srv=server.create_server(('127.0.0.1',0),trusted_peers={'127.0.0.1'},viewer_ip='127.0.0.1',data_dir=Path(tmp));threading.Thread(target=srv.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{srv.server_port}'
   def request(path,body=None,method=None,headers=None):
    req=urllib.request.Request(base+path,data=None if body is None else json.dumps(body).encode(),method=method,headers=headers or {'Origin':base,'Content-Type':'application/json'});return json.load(urllib.request.urlopen(req))
   try:
    c=request('/api/config');c['title']='사용자가 방금 바꾼 제목';editor={'X-Ingress-Path':'/api/hassio_ingress/test','Origin':'https://ha.invalid','Content-Type':'application/json'};request('/api/config',c,'PUT',editor)
    response=request('/api/appearance',{'color_mode':'light'},'POST');after=request('/api/config')
    self.assertEqual(after['color_mode'],'light');self.assertEqual(after['rooms'],c['rooms']);self.assertEqual(after['title'],c['title']);self.assertEqual(response['config'],after)
    for payload in [{'color_mode':'dark','rooms':[]},{'theme_id':'ember'},{'color_mode':'auto'}]:
     with self.assertRaises(urllib.error.HTTPError):request('/api/appearance',payload,'POST')
    with self.assertRaises(urllib.error.HTTPError):request('/api/appearance',{'color_mode':'dark'},'POST',{'Origin':'https://evil.invalid','Content-Type':'application/json'})
   finally:srv.shutdown();srv.server_close()
