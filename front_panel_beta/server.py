"""Standalone panel, HA-protected editor and scoped light/switch control."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from html import escape
from urllib.parse import urlsplit,parse_qs
from urllib.request import Request,build_opener,HTTPRedirectHandler
from ha_bridge import HAClient,HAReadError,CONTROL_DOMAINS
from panel_config import DEFAULT,validate,selected_ids,meta
from home_config import validate_home
from header_icon import read_icon
from device_controls import ACTION_DOMAINS
from music_bridge import MusicBridge,MusicAPI,MusicError
from music_search import SongSearch
from music_connection import MusicConnections,SupervisorDiscovery,ConnectionError as MusicConnectionError

import copy,ipaddress,json,os,re,secrets,signal,tempfile,threading,time
ROOT=Path(__file__).parent/'www'
ROUTES={'/':('index.html','text/html; charset=utf-8'),'/index.html':('index.html','text/html; charset=utf-8'),'/style.css':('style.css','text/css; charset=utf-8'),'/runtime.css':('runtime.css','text/css; charset=utf-8'),'/app.js':('app.js','text/javascript; charset=utf-8'),'/ui.js':('ui.js','text/javascript; charset=utf-8'),'/panel-ko.ttf':('panel-ko.ttf','font/ttf'),'/panel-ko.woff2':('panel-ko.woff2','font/woff2'),'/OFL.txt':('OFL.txt','text/plain; charset=utf-8'),'/editor':('editor.html','text/html; charset=utf-8'),'/editor.js':('editor.js','text/javascript; charset=utf-8'),'/editor.css':('editor.css','text/css; charset=utf-8')}

ROUTES['/device-controls.js']=('device-controls.js','text/javascript; charset=utf-8')
ROUTES['/device-controls.css']=('device-controls.css','text/css; charset=utf-8')
ROUTES['/music-setup.js']=('music-setup.js','text/javascript; charset=utf-8')
ROUTES['/music-setup.css']=('music-setup.css','text/css; charset=utf-8')
ROUTES['/music.js']=('music.js','text/javascript; charset=utf-8')
ROUTES['/music.css']=('music.css','text/css; charset=utf-8')
ROUTES['/appearance.css']=('appearance.css','text/css; charset=utf-8')
ROUTES['/glass.css']=('glass.css','text/css; charset=utf-8')
ROUTES['/home.css']=('home.css','text/css; charset=utf-8')
ROUTES['/home.js']=('home.js','text/javascript; charset=utf-8')
ROUTES['/addon-icon.png']=('addon-icon.png','image/png')

def initial_theme_document(document,settings):
 # Emit only validated presentation tokens, never the complete household configuration.
 colors={'background':'bg','surface':'surface','text':'text','muted':'muted','accent':'accent','active':'active','line':'line','onActive':'on-active','onAccent':'on-accent','switchOn':'switch-on','switchOff':'switch-off','thumb':'thumb','soft':'soft','iconBgOff':'icon-bg-off','iconBgOn':'icon-bg-on','iconOff':'icon-off','iconOn':'icon-on','activeBorder':'active-border','hover':'hover'}
 theme=settings['theme'];tokens=[]
 for key,css in colors.items():
  value=theme[key]
  if not isinstance(value,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',value):raise ValueError('Invalid startup color')
  tokens.append('--'+css+':'+value)
 for key in ['radius','gap','columns','cardHeight','fontSize']:
  value=theme[key]
  if type(value) is not int:raise ValueError('Invalid startup size')
  tokens.append('--'+key+':'+str(value)+('' if key=='columns' else 'px'))
 tokens.append('--motion:'+str(settings['motion']['duration'] if settings['motion']['enabled'] else 0)+'ms')
 tokens.append('color-scheme:'+settings['color_mode'])
 nonce=secrets.token_urlsafe(24)
 attributes=' data-theme="'+escape(settings['theme_id'],quote=True)+'" data-mode="'+escape(settings['color_mode'],quote=True)+'"'+(' class="no-motion"' if not settings['motion']['enabled'] else '')
 text=document.decode('utf-8').replace('<html lang="ko">','<html lang="ko"'+attributes+'>',1)
 style='<style id="startup-theme" nonce="'+nonce+'">:root{'+(';'.join(tokens))+'}</style>'
 return text.replace('</head>',style+'</head>',1).encode('utf-8'),nonce

def validate_viewer_ip(value):
 if value=='':return value
 if not isinstance(value,str):raise ValueError('viewer_ip must be an exact private IPv4 address')
 ip=ipaddress.ip_address(value)
 if ip.version!=4 or str(ip)!=value or not (ip.is_loopback or any(ip in ipaddress.ip_network(n) for n in ['10.0.0.0/8','172.16.0.0/12','192.168.0.0/16'])):raise ValueError('viewer_ip must be an exact private IPv4 address')
 return value

def validate_viewer_network(value):
 if value=='':return None
 if not isinstance(value,str):raise ValueError('viewer_network must be a private IPv4 CIDR')
 network=ipaddress.ip_network(value,strict=True)
 if network.version!=4 or network.prefixlen<24 or str(network)!=value or not any(network.subnet_of(ipaddress.ip_network(n)) for n in ['10.0.0.0/8','172.16.0.0/12','192.168.0.0/16']):raise ValueError('viewer_network must be a private IPv4 CIDR')
 return network

def validate_music_ingress_path(value):
 if value=='':return value
 if not isinstance(value,str) or not re.fullmatch(r'/api/hassio_ingress/[A-Za-z0-9_-]{1,200}/',value):raise ValueError('Music Assistant Ingress 경로 형식 오류')
 return value

def validate_music_url(value):
 if not isinstance(value,str) or not 1<=len(value)<=2048 or re.search(r'[\x00-\x20\\]',value):raise ValueError('Music Assistant 주소 형식 오류')
 p=urlsplit(value)
 if p.scheme not in ['http','https'] or not p.hostname or p.username is not None or p.password is not None or p.query or p.fragment or not re.fullmatch(r'[A-Za-z0-9.:-]+',p.hostname):raise ValueError('Music Assistant HTTP(S) 주소가 필요합니다')
 try:port=p.port
 except ValueError:raise ValueError('Music Assistant 포트 오류') from None
 return value,p.scheme+'://'+p.netloc

class MusicServerHealth:
 def __init__(self,url):
  self.url=url.rstrip('/')+'/info';self.lock=threading.Lock();self.until=0;self.result=None
 def check(self):
  with self.lock:
   if self.result is not None and time.monotonic()<self.until:return dict(self.result)
   connected=False
   class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None
   try:
    with build_opener(NoRedirect).open(Request(self.url,headers={'Accept':'application/json'}),timeout=3) as r:
     raw=r.read(65537)
     if len(raw)<=65536:
      d=json.loads(raw);connected=isinstance(d,dict) and isinstance(d.get('server_id'),str) and bool(d['server_id']) and isinstance(d.get('server_version'),str) and bool(d['server_version']) and d.get('status')=='running'
   except (OSError,ValueError,TimeoutError):pass
   self.result={'connected':bool(connected),'checked_at':int(time.time())};self.until=time.monotonic()+10
   return dict(self.result)

def create_server(address,trusted_peers=frozenset({'172.30.32.2'}),data_dir=None,ha_client=None,viewer_ip='',music_url='http://homeassistant.local:8095/',viewer_network='',music_ingress_path='',music_discovery=None,music_api_url="",music_api_token="",music_rpc=None):
 viewer_ip=validate_viewer_ip(viewer_ip)
 viewer_network=validate_viewer_network(viewer_network)
 music_url,_=validate_music_url(music_url)
 music_ingress_path=validate_music_ingress_path(music_ingress_path)
 music_health=MusicServerHealth(music_url)
 temporary=tempfile.TemporaryDirectory() if data_dir is None else None
 data_dir=Path(data_dir or temporary.name);data_dir.mkdir(parents=True,exist_ok=True)
 config_path=data_dir/'panel.json';lock=threading.RLock()
 music_connections=MusicConnections(data_dir,music_discovery,music_url,music_ingress_path)
 music_api=MusicAPI(data_dir,music_api_url,music_api_token)
 music_api.connection_url=lambda:music_connections.resolve()["url"]
 music=MusicBridge(music_rpc if music_rpc is not None else music_api,song_search=SongSearch() if music_rpc is None else None)
 raw=json.loads(config_path.read_text()) if config_path.exists() else DEFAULT
 config=validate(raw)
 if raw!=config and config_path.exists():
  backup=data_dir/'panel.pre-v828.json'
  if not backup.exists():backup.write_text(json.dumps(raw,ensure_ascii=False));os.chmod(backup,0o600)
  temp=config_path.with_suffix('.tmp');temp.write_text(json.dumps(config,ensure_ascii=False));os.chmod(temp,0o600);os.replace(temp,config_path)
 command_times={};confirmations={};revision=secrets.token_hex(8)
 class Handler(BaseHTTPRequestHandler):
  def _json(self,status,value,headers=None):self._send(status,json.dumps(value,ensure_ascii=False).encode(),'application/json; charset=utf-8',headers)
  def _send(self,status,data,ctype,headers=None,style_nonce=None):
   self.send_response(status);self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(data)))
   self.send_header('Cache-Control','no-store' if ctype.startswith(('text/html','application/json')) or urlsplit(self.path).path=='/api/header-icon' else 'private, max-age=3600')
   self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer')
   origin=music_connections.frame_origin();frame_origin=(' '+origin) if origin else ''
   style_policy="style-src 'self'"+(" 'nonce-"+style_nonce+"'" if style_nonce else '')
   self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; "+style_policy+"; img-src 'self' data:; connect-src 'self'; frame-src 'self'"+frame_origin+"; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'self'")
   for k,v in (headers or {}).items():self.send_header(k,v)
   self.end_headers();self.wfile.write(data)
  def _ingress(self):return self.client_address[0] in trusted_peers and bool(re.fullmatch(r'/api/hassio_ingress/[A-Za-z0-9_-]+/?',self.headers.get('X-Ingress-Path','')))
  def _viewer(self):return self._private() and bool((viewer_ip and self.client_address[0]==viewer_ip) or (viewer_network is not None and ipaddress.ip_address(self.client_address[0]) in viewer_network))
  def _peer_allowed(self):return self._ingress() or self._viewer()
  def _role(self):
   if self._ingress():return 'editor'
   return 'viewer' if self._viewer() else None
  def _private(self):
   ip=ipaddress.ip_address(self.client_address[0]);return ip.is_loopback or any(ip in ipaddress.ip_network(n) for n in ['10.0.0.0/8','172.16.0.0/12','192.168.0.0/16'])
  def _origin(self):return self._ingress() or self.headers.get('Origin','') in ('http://'+self.headers.get('Host',''),'https://'+self.headers.get('Host',''))
  def _body(self):
   n=int(self.headers.get('Content-Length','0'))
   if not 0<n<=65536 or self.headers.get('Content-Type','').split(';')[0]!='application/json':raise ValueError('JSON 본문 오류')
   return json.loads(self.rfile.read(n))
  def _device_card(self,body):
   if not isinstance(body,dict) or not all(isinstance(body.get(k),str) and len(body[k])<=64 for k in ['room_id','card_id']):return None
   with lock:
    room=next((r for r in config['rooms'] if r['id']==body['room_id']),None)
    card=next((c for c in room['cards'] if c['id']==body['card_id']),None) if room else None
    return card['entity_id'] if card and card['visible'] and card['control'] and card['entity_id'].split('.')[0] in ACTION_DOMAINS else None
  def do_GET(self):
   if not self._private() or not self._peer_allowed():self.send_error(403);return
   path=urlsplit(self.path).path;role=self._role()
   if path in ['/','/index.html'] and self._ingress() and urlsplit(self.path).query!='view=panel':self._send(303,b'','text/plain',{'Location':'./editor'});return
   if path=='/health':self._json(200,{'status':'ok','version':'1.1.0-beta.29','standalone':True,'ha_read_api':ha_client is not None,'ha_control':ha_client is not None});return
   if not role:self.send_error(403);return
   if path in ['/editor','/editor.js','/api/entities','/api/music/setup','/api/music/discover','/api/music/auth','/music-setup.js'] and role!='editor':self.send_error(403);return
   if path=='/api/device-controls':
    query=parse_qs(urlsplit(self.path).query)
    if set(query)!={'room_id','card_id'} or any(len(v)!=1 for v in query.values()):self.send_error(400);return
    eid=self._device_card({k:v[0] for k,v in query.items()})
    if eid is None:self.send_error(403);return
    if ha_client is None:self._json(503,{'error':'HA 연결이 준비되지 않았습니다'});return
    try:self._json(200,ha_client.device_controls(eid))
    except HAReadError as error:self._json(502,{'error':str(error)})
    return
   if path=='/api/music/auth':self._json(200,{'configured':music_api.configured()});return
   if path in ['/api/music/state','/api/music/library','/api/music/search','/api/music/children','/api/music/queue','/api/music/art']:
    with lock:enabled=config['music_assistant']['enabled']
    if not enabled:self._json(403,{'error':'Music Assistant 사용이 꺼져 있습니다'});return
    query=parse_qs(urlsplit(self.path).query,keep_blank_values=True);allowed={'/api/music/state':({'player_id'},set()),'/api/music/library':({'category','offset'},{'category'}),'/api/music/search':({'q','offset'},{'q'}),'/api/music/children':({'item_id','offset','view'},{'item_id'}),'/api/music/queue':({'player_id','offset'},{'player_id'}),'/api/music/art':({'id'},{'id'})}[path]
    if not allowed[1]<=set(query) or set(query)-allowed[0] or any(len(v)!=1 or len(v[0])>240 for v in query.values()):self._json(400,{'error':'음악 요청 형식 오류'});return
    q={k:v[0] for k,v in query.items()}
    try:
     offset=int(q.get('offset','0'))
     if path=='/api/music/state':result=music.snapshot(q.get('player_id',''))
     elif path=='/api/music/library':result=music.library(q['category'],offset)
     elif path=='/api/music/search':result=music.search(q['q'],offset)
     elif path=='/api/music/children':result=music.children(q['item_id'],offset,q.get('view','tracks'))
     elif path=='/api/music/queue':result=music.queue(q['player_id'],offset)
     else:
      data,mime=music.image(q['id']);self._send(200,data,mime,{'Cache-Control':'private, max-age=300'});return
     self._json(200,result)
    except (MusicError,ValueError) as error:self._json(getattr(error,'status',400),{'error':str(error) if isinstance(error,MusicError) else '음악 요청 값 오류'})
    return
   if path=='/api/music/setup':self._json(200,music_connections.public());return
   if path=='/api/music/discover':
    try:self._json(200,{'addons':music_connections.discover()})
    except MusicConnectionError as error:self._json(400,{'error':str(error)})
    return
   if path=='/api/config':
    with lock:self._json(200,config)
    return
   if path=='/api/music/status':
    with lock:enabled=config['music_assistant']['enabled']
    if not enabled:self._json(403,{'error':'Music Assistant 사용이 꺼져 있습니다'});return
    try:self._json(200,music_health.check() if music_connections.selection is None else music_connections.status())
    except MusicConnectionError:self._json(200,{'connected':False,'checked_at':int(time.time())})
    return
   if path=='/api/music/native':
    with lock:enabled=config['music_assistant']['enabled']
    if not enabled:self._json(403,{'error':'Music Assistant 사용이 꺼져 있습니다'});return
    try:connection=music_connections.resolve()
    except MusicConnectionError as error:self._json(503,{'error':str(error)});return
    via_ha=bool(self._ingress() and connection['ingress_path'])
    self._json(200,{'url':connection['ingress_path'] if via_ha else connection['url'],'native':True,'login_required':True,'via_ha':via_ha})
    return
   if path=='/api/header-icon':
    with lock:icon_path=config['display']['header_icon'];visible=config['display']['header']
    if not visible or not icon_path:self.send_error(404);return
    try:data,mime=read_icon(icon_path)
    except ValueError as error:self._json(502,{'error':str(error)});return
    self._send(200,data,mime);return
   if path=='/api/meta':self._json(200,meta());return
   if path=='/api/revision':self._json(200,{'revision':revision,'music_revision':music_connections.revision()});return
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
    name,ctype=ROUTES[path];data=(ROOT/name).read_bytes();nonce=None
    if name in ['index.html','editor.html']:
     with lock:settings=copy.deepcopy(config)
     if settings['music_assistant']['enabled'] and music_connections.selection:
      try:music_connections.resolve()
      except MusicConnectionError:pass
     data,nonce=initial_theme_document(data,settings)
    self._send(200,data,ctype,style_nonce=nonce);return
   self.send_error(404)
  def do_POST(self):
   nonlocal config,revision
   if not self._private() or not self._peer_allowed() or not self._origin():self.send_error(403);return
   path=urlsplit(self.path).path
   if path not in ['/api/control','/api/appearance','/api/home-settings','/api/device-confirm','/api/device-action','/api/music/setup/test','/api/music/setup/save','/api/music/action','/api/music/confirm','/api/music/auth']:self.send_error(404);return
   if path in ['/api/control','/api/appearance'] and not self._role():self.send_error(403);return
   try:body=self._body()
   except (ValueError,TypeError):self.send_error(400);return
   if not isinstance(body,dict):self.send_error(400);return

   if path in ['/api/music/action','/api/music/confirm','/api/music/auth']:
    if path=='/api/music/auth' and self._role()!='editor':self.send_error(403);return
    with lock:enabled=config['music_assistant']['enabled']
    if path!='/api/music/auth' and not enabled:self._json(403,{'error':'Music Assistant 사용이 꺼져 있습니다'});return
    try:
     if path=='/api/music/auth':
      if set(body)!={'token'}:raise MusicError('인증 요청 형식 오류')
      result=music_api.authenticate(music_connections.resolve()['url'],body['token']);music.reset();revision=secrets.token_hex(8)
     elif path=='/api/music/confirm':
      if set(body)!={'player_id','item_id','mode'}:raise MusicError('재생 확인 요청 형식 오류')
      result=music.confirm(body['player_id'],body['item_id'],body['mode'],self.client_address[0])
     else:result=music.action(body,self.client_address[0])
     self._json(200,result)
    except (MusicError,MusicConnectionError) as error:self._json(getattr(error,'status',400),{'error':str(error)})
    except OSError:self._json(500,{'error':'음악 연결 설정을 저장하지 못했습니다.'})
    return
   if path in ['/api/music/setup/test','/api/music/setup/save']:
    if self._role()!='editor':self.send_error(403);return
    try:
     if path.endswith('/test'):self._json(200,music_connections.test(body));return
     resolved=music_connections.candidate(body)
     with lock:
      old_selection=copy.deepcopy(music_connections.selection)
      music_connections.commit(body,resolved)
      try:
       new=copy.deepcopy(config);new['music_assistant']['enabled']=True;new=validate(new)
       if new!=config:
        temp=config_path.with_suffix('.tmp');temp.write_text(json.dumps(new,ensure_ascii=False));os.chmod(temp,0o600);os.replace(temp,config_path);config=new
       revision=secrets.token_hex(8)
      except (OSError,ValueError):music_connections.restore(old_selection);raise
     self._json(200,{'saved':True,'enabled':True,'connection':music_connections.public()})
    except MusicConnectionError as error:self._json(400,{'error':str(error)})
    except OSError:self._json(500,{'error':'연결 설정을 저장하지 못했습니다. 설정을 다시 확인해 주세요.'})
    return
   if path in ['/api/device-confirm','/api/device-action']:
    required={'room_id','card_id','action'}
    if path=='/api/device-action':required.add('params')
    if not required<=set(body) or set(body)-required-({'confirmation'} if path=='/api/device-action' else set()) or not isinstance(body.get('action'),str):self.send_error(400);return
    eid=self._device_card(body)
    if eid is None:self.send_error(403);return
    is_lock=eid.startswith('lock.')
    if path=='/api/device-confirm':
     if not is_lock or body['action'] not in ['lock','unlock']:self.send_error(400);return
     with lock:
      now=time.monotonic()
      for key in list(confirmations):
       if confirmations[key][-1]<=now:del confirmations[key]
      if len(confirmations)>=256:confirmations.pop(next(iter(confirmations)))
      token=secrets.token_urlsafe(24);confirmations[token]=(self.client_address[0],body['room_id'],body['card_id'],eid,body['action'],now+30)
     self._json(200,{'confirmation':token,'expires_in':30});return
    if not isinstance(body['params'],dict):self.send_error(400);return
    with lock:
     now=time.monotonic()
     if is_lock:
      token=body.get('confirmation');proof=confirmations.pop(token,None) if isinstance(token,str) else None
      if not proof or proof[:-1]!=(self.client_address[0],body['room_id'],body['card_id'],eid,body['action']) or proof[-1]<=now:self._json(403,{'error':'잠금 동작을 다시 확인해 주세요.'});return
     if command_times.get(eid,0)>now-.4:self._json(429,{'error':'현재 상태를 확인한 뒤 다시 눌러 주세요.'});return
     command_times[eid]=now
    if ha_client is None:self._json(503,{'error':'HA 연결이 준비되지 않았습니다'});return
    try:self._json(200,ha_client.device_action(eid,body['action'],body['params']))
    except ValueError as error:self._json(400,{'error':str(error)})
    except HAReadError as error:self._json(502,{'error':str(error)})
    return
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

def run_server(srv):
 def terminate(signum,frame):raise SystemExit(0)
 previous=signal.signal(signal.SIGTERM,terminate)
 try:srv.serve_forever()
 except KeyboardInterrupt:pass
 finally:
  srv.server_close()
  signal.signal(signal.SIGTERM,previous)

if __name__=='__main__':
 options=json.loads(Path('/data/options.json').read_text())
 data=Path('/data/panel');data.mkdir(exist_ok=True)
 if os.geteuid()==0:os.chown(data,65534,65534);os.setgroups([]);os.setgid(65534);os.setuid(65534)
 print('Front Panel Beta 1.1.0-beta.29; optional Music Assistant',flush=True)
 run_server(create_server(('0.0.0.0',8099),data_dir=data,ha_client=HAClient(os.environ.get('SUPERVISOR_TOKEN','')),viewer_ip=options.get('viewer_ip',''),viewer_network=options.get('viewer_network',''),music_url=options.get('music_assistant_url','http://homeassistant.local:8095/'),music_ingress_path=options.get('music_assistant_ingress_path',''),music_discovery=SupervisorDiscovery(os.environ.get('SUPERVISOR_TOKEN','')),music_api_url=options.get('music_api_url',''),music_api_token=options.get('music_api_token','')))
