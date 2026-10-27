"""Standalone panel, HA-protected editor and scoped light/switch control."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from ha_bridge import HAClient,HAReadError,CONTROL_DOMAINS
from panel_config import DEFAULT,validate,selected_ids,meta
from home_config import validate_home
from header_icon import read_icon
import copy,ipaddress,json,os,re,secrets,tempfile,threading,time
ROOT=Path(__file__).parent/'www'
ROUTES={'/':('index.html','text/html; charset=utf-8'),'/index.html':('index.html','text/html; charset=utf-8'),'/style.css':('style.css','text/css; charset=utf-8'),'/runtime.css':('runtime.css','text/css; charset=utf-8'),'/app.js':('app.js','text/javascript; charset=utf-8'),'/ui.js':('ui.js','text/javascript; charset=utf-8'),'/panel-ko.ttf':('panel-ko.ttf','font/ttf'),'/panel-ko.woff2':('panel-ko.woff2','font/woff2'),'/OFL.txt':('OFL.txt','text/plain; charset=utf-8'),'/editor':('editor.html','text/html; charset=utf-8'),'/editor.js':('editor.js','text/javascript; charset=utf-8'),'/editor.css':('editor.css','text/css; charset=utf-8')}

ROUTES['/appearance.css']=('appearance.css','text/css; charset=utf-8')
ROUTES['/glass.css']=('glass.css','text/css; charset=utf-8')
ROUTES['/home.css']=('home.css','text/css; charset=utf-8')
ROUTES['/home.js']=('home.js','text/javascript; charset=utf-8')
ROUTES['/addon-icon.png']=('addon-icon.png','image/png')

def validate_viewer_ip(value):
 if value=='':return value
 if not isinstance(value,str):raise ValueError('viewer_ip must be an exact private IPv4 address')
 ip=ipaddress.ip_address(value)
 if ip.version!=4 or str(ip)!=value or not (ip.is_loopback or any(ip in ipaddress.ip_network(n) for n in ['10.0.0.0/8','172.16.0.0/12','192.168.0.0/16'])):raise ValueError('viewer_ip must be an exact private IPv4 address')
 return value

def create_server(address,trusted_peers=frozenset({'172.30.32.2'}),data_dir=None,ha_client=None,viewer_ip=''):
 viewer_ip=validate_viewer_ip(viewer_ip)
 temporary=tempfile.TemporaryDirectory() if data_dir is None else None
 data_dir=Path(data_dir or temporary.name);data_dir.mkdir(parents=True,exist_ok=True)
 config_path=data_dir/'panel.json';lock=threading.RLock()
 raw=json.loads(config_path.read_text()) if config_path.exists() else DEFAULT
 config=validate(raw)
 if raw!=config and config_path.exists():
  backup=data_dir/'panel.pre-v828.json'
  if not backup.exists():backup.write_text(json.dumps(raw,ensure_ascii=False));os.chmod(backup,0o600)
  temp=config_path.with_suffix('.tmp');temp.write_text(json.dumps(config,ensure_ascii=False));os.chmod(temp,0o600);os.replace(temp,config_path)
 command_times={};revision=secrets.token_hex(8)
 class Handler(BaseHTTPRequestHandler):
  def _json(self,status,value,headers=None):self._send(status,json.dumps(value,ensure_ascii=False).encode(),'application/json; charset=utf-8',headers)
  def _send(self,status,data,ctype,headers=None):
   self.send_response(status);self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(data)))
   self.send_header('Cache-Control','no-store' if ctype.startswith(('text/html','application/json')) or urlsplit(self.path).path=='/api/header-icon' else 'private, max-age=3600')
   self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer')
   self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'self'")
   for k,v in (headers or {}).items():self.send_header(k,v)
   self.end_headers();self.wfile.write(data)
  def _ingress(self):return self.client_address[0] in trusted_peers and bool(re.fullmatch(r'/api/hassio_ingress/[A-Za-z0-9_-]+/?',self.headers.get('X-Ingress-Path','')))
  def _peer_allowed(self):return self._ingress() or bool(viewer_ip and self.client_address[0]==viewer_ip)
  def _role(self):
   if self._ingress():return 'editor'
   return 'viewer' if self._private() and viewer_ip and self.client_address[0]==viewer_ip else None
  def _private(self):
   ip=ipaddress.ip_address(self.client_address[0]);return ip.is_loopback or any(ip in ipaddress.ip_network(n) for n in ['10.0.0.0/8','172.16.0.0/12','192.168.0.0/16'])
  def _origin(self):return self._ingress() or self.headers.get('Origin','') in ('http://'+self.headers.get('Host',''),'https://'+self.headers.get('Host',''))
  def _body(self):
   n=int(self.headers.get('Content-Length','0'))
   if not 0<n<=65536 or self.headers.get('Content-Type','').split(';')[0]!='application/json':raise ValueError('JSON 본문 오류')
   return json.loads(self.rfile.read(n))
  def do_GET(self):
   if not self._private() or not self._peer_allowed():self.send_error(403);return
   path=urlsplit(self.path).path;role=self._role()
   if path in ['/','/index.html'] and self._ingress() and urlsplit(self.path).query!='view=panel':self._send(303,b'','text/plain',{'Location':'./editor'});return
   if path=='/health':self._json(200,{'status':'ok','version':'1.0.0','standalone':True,'ha_read_api':ha_client is not None,'ha_control':ha_client is not None});return
   if not role:self.send_error(403);return
   if path in ['/editor','/editor.js','/api/entities'] and role!='editor':self.send_error(403);return
   if path=='/api/config':
    with lock:self._json(200,config)
    return
   if path=='/api/header-icon':
    with lock:icon_path=config['display']['header_icon'];visible=config['display']['header']
    if not visible or not icon_path:self.send_error(404);return
    try:data,mime=read_icon(icon_path)
    except ValueError as error:self._json(502,{'error':str(error)});return
    self._send(200,data,mime);return
   if path=='/api/meta':self._json(200,meta());return
   if path=='/api/revision':self._json(200,{'revision':revision});return
   if path=='/api/home-data':
    with lock:home=copy.deepcopy(config['home'])
    todos=[]
    if home['enabled'] and home['todos']['enabled']:
     for item in home['todos']['lists']:
      result={**item,'items':[],'error':None}
      if not item['entity_id']:result['error']='미연결'
      elif ha_client is None:result['error']='HA 연결이 준비되지 않았습니다'
      else:
       try:result['items']=ha_client.todo_items(item['entity_id'])
       except HAReadError as error:result['error']=str(error)
      todos.append(result)
    self._json(200,{'todos':todos});return
   if path in ['/api/entities','/api/entity-states']:
    with lock:ids=selected_ids(config)
    if path=='/api/entity-states' and not ids:self._json(200,{'states':{},'control_enabled':True});return
    if ha_client is None:self._json(503,{'error':'HA 연결이 준비되지 않았습니다'});return
    try:self._json(200,{'entities':ha_client.catalog(),'control_enabled':True} if path=='/api/entities' else {'states':ha_client.states(ids),'control_enabled':True})
    except HAReadError as error:self._json(502,{'error':str(error)})
    return
   if path in ROUTES:
    name,ctype=ROUTES[path];self._send(200,(ROOT/name).read_bytes(),ctype);return
   self.send_error(404)
  def do_POST(self):
   nonlocal config,revision
   if not self._private() or not self._peer_allowed() or not self._origin():self.send_error(403);return
   path=urlsplit(self.path).path
   if path not in ['/api/control','/api/appearance','/api/home-settings']:self.send_error(404);return
   if path in ['/api/control','/api/appearance'] and not self._role():self.send_error(403);return
   try:body=self._body()
   except (ValueError,TypeError):self.send_error(400);return
   if not isinstance(body,dict):self.send_error(400);return
   if path=='/api/home-settings':
    if self._role()!='editor':self.send_error(403);return
    try:home=validate_home(body)
    except (ValueError,TypeError,KeyError):self._json(400,{'error':'홈 설정 형식을 확인해 주세요'});return
    with lock:
     new=copy.deepcopy(config);new['home']=home;new=validate(new)
     temp=config_path.with_suffix('.tmp');temp.write_text(json.dumps(new,ensure_ascii=False));os.chmod(temp,0o600);os.replace(temp,config_path);config=new;revision=secrets.token_hex(8)
     self._json(200,{'saved':True,'revision':revision})
    return
   if path=='/api/appearance':
    if set(body)!={'color_mode'} or body['color_mode'] not in ['light','dark']:self.send_error(400);return
    with lock:
     new=copy.deepcopy(config);new['color_mode']=body['color_mode'];new=validate(new)
     temp=config_path.with_suffix('.tmp');temp.write_text(json.dumps(new,ensure_ascii=False));os.chmod(temp,0o600);os.replace(temp,config_path);config=new;revision=secrets.token_hex(8)
     self._json(200,{'config':config,'revision':revision})
    return
   if path=='/api/control':
    if set(body)!={'room_id','card_id','state'} or body['state'] not in ['on','off']:self.send_error(400);return
    with lock:
     room=next((r for r in config['rooms'] if r['id']==body['room_id']),None)
     card=next((c for c in room['cards'] if c['id']==body['card_id']),None) if room else None
     if not card or not card['visible'] or not card['control'] or card['entity_id'].split('.')[0] not in CONTROL_DOMAINS:self.send_error(403);return
     eid=card['entity_id'];now=time.monotonic()
     if command_times.get(eid,0)>now-.4:self._json(429,{'error':'상태 확인 후 다시 눌러 주세요'});return
     command_times[eid]=now
    if ha_client is None:self._json(503,{'error':'HA 연결이 준비되지 않았습니다'});return
    try:self._json(200,ha_client.set_state(eid,body['state']))
    except HAReadError as error:self._json(502,{'error':str(error)})
    return
  def do_PUT(self):
   nonlocal config,revision
   if not self._private() or not self._peer_allowed() or self._role()!='editor' or not self._origin():self.send_error(403);return
   if urlsplit(self.path).path!='/api/config':self.send_error(404);return
   try:
    new=validate(self._body())
    with lock:
     temp=config_path.with_suffix('.tmp');temp.write_text(json.dumps(new,ensure_ascii=False));os.chmod(temp,0o600);os.replace(temp,config_path);config=new;revision=secrets.token_hex(8)
   except (ValueError,TypeError,KeyError):self._json(400,{'error':'설정 값·방·카드·엔티티 형식을 확인해 주세요'});return
   self._json(200,{'saved':True,'revision':revision})
  def log_message(self,format,*args):print(self.client_address[0],format%args,flush=True)
 srv=ThreadingHTTPServer(address,Handler);srv.daemon_threads=True;srv.temporary=temporary;return srv

if __name__=='__main__':
 options=json.loads(Path('/data/options.json').read_text())
 data=Path('/data/panel');data.mkdir(exist_ok=True)
 if os.geteuid()==0:os.chown(data,65534,65534);os.setgroups([]);os.setgid(65534);os.setuid(65534)
 print('Front Panel 1.0.0; scoped light/switch/automation control enabled',flush=True)
 create_server(('0.0.0.0',8099),data_dir=data,ha_client=HAClient(os.environ.get('SUPERVISOR_TOKEN','')),viewer_ip=options.get('viewer_ip','')).serve_forever()
