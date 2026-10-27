import copy,json,tempfile,threading,unittest,urllib.request,urllib.error
from pathlib import Path
import server

class FakeHA:
    def catalog(self):return [{'entity_id':'light.example','name':'테스트 조명','state':'on','unit':'','domain':'light'}]
    def states(self,ids):return {eid:{'entity_id':eid,'name':'테스트 조명','state':'on','unit':''} for eid in ids}

class EntityBridgeTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.srv=server.create_server(('127.0.0.1',0),trusted_peers={'127.0.0.1'},data_dir=Path(self.tmp.name),ha_client=FakeHA())
        threading.Thread(target=self.srv.serve_forever,daemon=True).start();self.base=f'http://127.0.0.1:{self.srv.server_port}'
        self.headers={'X-Ingress-Path':'/api/hassio_ingress/test','Origin':'https://ha.invalid'}
    def tearDown(self):self.srv.shutdown();self.srv.server_close();self.tmp.cleanup()
    def get(self,path,headers=None):return json.load(urllib.request.urlopen(urllib.request.Request(self.base+path,headers=headers or {})))
    def test_catalog_requires_editor(self):
        self.assertEqual(self.get('/api/entities',self.headers)['entities'][0]['entity_id'],'light.example')
        with self.assertRaises(urllib.error.HTTPError) as ctx:self.get('/api/entities')
        self.assertEqual(ctx.exception.code,403)
    def test_only_selected_states_returned(self):
        self.assertEqual(self.get('/api/entity-states')['states'],{})
        config=self.get('/api/config',self.headers);config['rooms'][0]['cards'][0]['entity_id']='light.example'
        req=urllib.request.Request(self.base+'/api/config',method='PUT',headers={**self.headers,'Content-Type':'application/json'},data=json.dumps(config).encode());urllib.request.urlopen(req).close()
        response=self.get('/api/entity-states');self.assertEqual(set(response['states']),{'light.example'});self.assertTrue(response['control_enabled'])
    def test_legacy_settings_migrate_and_bad_ids_rejected(self):
        config=json.loads((Path(__file__).parent/'fixtures/legacy-v3.json').read_text());config.pop('bindings');migrated=server.validate(config)
        self.assertIn('rooms',migrated)
        migrated['rooms'][0]['sensors'][0]['entity_id']='../../api/config'
        with self.assertRaises(ValueError):server.validate(migrated)
    def test_control_without_registered_card_rejected(self):
        req=urllib.request.Request(self.base+'/api/control',method='POST',headers={**self.headers,'Content-Type':'application/json'},data=b'{}')
        with self.assertRaises(urllib.error.HTTPError) as ctx:urllib.request.urlopen(req)
        self.assertEqual(ctx.exception.code,400)
