import copy,json,tempfile,threading,unittest,urllib.request,urllib.error
from pathlib import Path
import server
class HomeHA:
 def __init__(self):self.calls=[]
 def todo_items(self,eid):self.calls.append(eid);return [{'summary':'테스트 항목','due':''}]
class HomeAPITest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.ha=HomeHA();self.srv=server.create_server(('127.0.0.1',0),trusted_peers={'127.0.0.1'},viewer_ip='127.0.0.1',data_dir=Path(self.tmp.name),ha_client=self.ha);threading.Thread(target=self.srv.serve_forever,daemon=True).start();self.base=f'http://127.0.0.1:{self.srv.server_port}';self.editor={'X-Ingress-Path':'/api/hassio_ingress/test','Origin':self.base}
 def tearDown(self):self.srv.shutdown();self.srv.server_close();self.tmp.cleanup()
 def request(self,path,method='GET',data=None,headers=None):
  req=urllib.request.Request(self.base+path,method=method,headers={**(headers or {}),**({'Content-Type':'application/json'} if data is not None else {})},data=json.dumps(data).encode() if data is not None else None)
  return json.load(urllib.request.urlopen(req))
 def test_home_todo_reads_only_saved_enabled_lists_and_mode_only_write(self):
  c=self.request('/api/config');h=copy.deepcopy(c['home']);h['enabled']=True;h['todos']['lists'][0]['entity_id']='todo.test'
  self.request('/api/home-settings','POST',h,self.editor)
  saved=self.request('/api/config');self.assertEqual(saved['rooms'],c['rooms']);self.assertEqual(saved['home'],h)
  data=self.request('/api/home-data');self.assertEqual(self.ha.calls,['todo.test']);self.assertEqual(data['todos'][0]['items'][0]['summary'],'테스트 항목')
  with self.assertRaises(urllib.error.HTTPError) as ctx:self.request('/api/home-settings','POST',h,{'Origin':self.base})
  self.assertEqual(ctx.exception.code,403)
  with self.assertRaises(urllib.error.HTTPError):self.request('/api/home-settings','POST',{**h,'entity_id':'todo.arbitrary'},self.editor)
  h['enabled']=False;self.request('/api/home-settings','POST',h,self.editor);self.ha.calls=[]
  self.assertEqual(self.request('/api/home-data')['todos'],[]);self.assertEqual(self.ha.calls,[])
