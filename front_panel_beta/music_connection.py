"""Private MA connection setup; Supervisor reads only, never app/device writes."""
import copy,hashlib,ipaddress,json,os,re,threading,time
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request,build_opener,HTTPRedirectHandler

class ConnectionError(ValueError):pass
class NoRedirect(HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None

def urlopen(request,timeout=5):return build_opener(NoRedirect).open(request,timeout=timeout)

def checked_url(value):
 if not isinstance(value,str) or not 1<=len(value)<=2048 or re.search(r'[\x00-\x20\\]',value):raise ConnectionError('MA HTTP(S) 주소를 확인해 주세요.')
 try:p=urlsplit(value);p.port
 except ValueError:raise ConnectionError('올바른 MA 서버 주소를 입력해 주세요.')
 if p.scheme not in ['http','https'] or not p.hostname or p.username is not None or p.password is not None or p.query or p.fragment or not re.fullmatch(r'[A-Za-z0-9.:-]+',p.hostname):raise ConnectionError('계정·암호가 포함되지 않은 MA HTTP(S) 주소가 필요합니다.')
 return value

def ma_slug(value):return isinstance(value,str) and len(value)<=128 and bool(re.fullmatch(r'[a-z0-9_]+',value)) and bool(re.search(r'(?:^|_)music_assistant(?:_(?:server|beta|dev|nightly))?$',value))

def probe_music(url):
 result={'connected':False,'checked_at':int(time.time())}
 try:
  with urlopen(Request(checked_url(url).rstrip('/')+'/info',headers={'Accept':'application/json'}),timeout=3) as response:raw=response.read(65537)
  if len(raw)>65536:return result
  data=json.loads(raw)
  if not isinstance(data,dict) or not isinstance(data.get('server_id'),str) or not data['server_id'] or not isinstance(data.get('server_version'),str) or not data['server_version'] or data.get('status')!='running':return result
  result.update(connected=True,server_version=data['server_version'][:80])
  if isinstance(data.get('internal_url'),str):result['internal_url']=data['internal_url']
 except (OSError,ValueError,TimeoutError):pass
 return result

class SupervisorDiscovery:
 def __init__(self,token):self.token=token
 def _get(self,path):
  if not self.token or not (path=='/supervisor/info' or re.fullmatch(r'/addons/[a-z0-9_]{1,128}/info',path)):raise ConnectionError('MA 애드온 조회 권한이 없습니다.')
  try:
   request=Request('http://supervisor'+path,headers={'Authorization':'Bearer '+self.token,'Accept':'application/json'},method='GET')
   with urlopen(request,timeout=5) as response:raw=response.read(2097153)
   if len(raw)>2097152:raise ValueError()
   result=json.loads(raw)
   if result.get('result')!='ok' or not isinstance(result.get('data'),dict):raise ValueError()
   return result['data']
  except (OSError,ValueError,TypeError,AttributeError,TimeoutError):raise ConnectionError('HA의 MA 애드온 정보를 읽지 못했습니다. 주소 직접 연결도 사용할 수 있습니다.') from None
 def discover(self):
  addons=self._get('/supervisor/info').get('addons')
  if not isinstance(addons,list):raise ConnectionError('설치된 애드온 목록을 읽지 못했습니다.')
  return [{'slug':x['slug'],'name':str(x.get('name','Music Assistant'))[:160],'state':str(x.get('state','unknown'))[:32],'version':str(x.get('version',''))[:80]} for x in addons if isinstance(x,dict) and ma_slug(x.get('slug')) and x.get('installed',True) is not False]
 def info(self,slug):
  if not ma_slug(slug):raise ConnectionError('Music Assistant 애드온만 선택할 수 있습니다.')
  result=self._get('/addons/'+slug+'/info')
  if result.get('slug')!=slug:raise ConnectionError('MA 애드온 식별 정보가 일치하지 않습니다.')
  return result

class MusicConnections:
 def __init__(self,directory,supervisor=None,legacy_url='http://homeassistant.local:8095/',legacy_ingress=''):
  self.path=Path(directory)/'music-connection.json';self.supervisor=supervisor;self.legacy_url=legacy_url;self.legacy_ingress=legacy_ingress;self.lock=threading.RLock();self.selection=None;self.cached=None;self.cache_until=0;self.status_cache=None;self.last_target=None;self.resolve_lock=threading.Lock()
  if self.path.exists():
   try:self.selection=self.validate(json.loads(self.path.read_text()))
   except (OSError,ValueError):self.selection={'mode':'error'}
 @staticmethod
 def validate(choice):
  if not isinstance(choice,dict):raise ConnectionError('MA 연결 설정 형식 오류')
  if choice.get('mode')=='auto' and set(choice)=={'mode','addon_slug'} and ma_slug(choice['addon_slug']):return dict(choice)
  if choice.get('mode')=='manual' and set(choice)=={'mode','url'}:return {'mode':'manual','url':checked_url(choice['url'])}
  raise ConnectionError('MA 연결 방식·애드온·주소를 확인해 주세요.')
 def public(self):
  choice=self.selection or {'mode':'legacy'}
  return {'mode':choice['mode'],'addon_slug':choice.get('addon_slug',''),'manual_url':choice.get('url',self.legacy_url),'discovery_available':self.supervisor is not None,'configured':self.selection is not None,'external_ready':bool(self.legacy_ingress) if self.selection is None else bool(self.cached and self.cached.get('ingress_path')) or choice.get('url','').startswith('https://')}
 def discover(self):
  if self.supervisor is None:raise ConnectionError('자동 검색은 HA 애드온 설치 환경에서 사용할 수 있습니다. 주소 직접 연결을 선택해 주세요.')
  return self.supervisor.discover()
 def candidate(self,choice):
  choice=self.validate(choice)
  if choice['mode']=='manual':
   health=probe_music(choice['url'])
   if not health.get('connected'):raise ConnectionError('MA에 연결하지 못했습니다. 서버 실행 상태와 주소를 확인해 주세요.')
   return {'url':choice['url'],'health_url':choice['url'],'ingress_path':'','name':'주소 직접 연결','server_version':health.get('server_version',''),'connected':True}
  if self.supervisor is None:raise ConnectionError('HA 애드온 자동 검색을 사용할 수 없습니다.')
  if not any(a['slug']==choice['addon_slug'] for a in self.supervisor.discover()):raise ConnectionError('설치된 MA 애드온을 다시 찾아 주세요.')
  info=self.supervisor.info(choice['addon_slug'])
  if info.get('state')!='started':raise ConnectionError('선택한 MA 애드온을 HA에서 먼저 실행해 주세요.')
  address=info.get('ip_address','')
  try:
   ip=ipaddress.ip_address(address)
   if ip.version!=4 or not (ip.is_loopback or any(ip in ipaddress.ip_network(n) for n in ['10.0.0.0/8','172.16.0.0/12','192.168.0.0/16'])):raise ValueError()
  except ValueError:raise ConnectionError('MA 애드온의 내부 접속 주소를 확인할 수 없습니다.') from None
  health_url='http://'+address+':8095/';health=probe_music(health_url)
  if not health.get('connected'):raise ConnectionError('MA 기본 웹 연결을 확인하지 못했습니다. 사용자 지정 포트라면 주소 직접 연결을 선택해 주세요.')
  url=health.get('internal_url')
  try:url=checked_url(url)
  except ConnectionError:url='http://homeassistant.local:'+str((info.get('network') or {}).get('8095/tcp') or 8095)+'/'
  ingress=info.get('ingress_url') or info.get('ingress_entry') or ''
  if not isinstance(ingress,str) or not re.fullmatch(r'/api/hassio_ingress/[A-Za-z0-9_-]{1,200}/?',ingress):raise ConnectionError('이 MA 애드온의 HA 접속 경로를 확인하지 못했습니다.')
  ingress=ingress.rstrip('/')+'/'
  return {'url':url,'health_url':health_url,'ingress_path':ingress,'name':str(info.get('name','Music Assistant'))[:160],'server_version':health.get('server_version',''),'connected':True}
 def test(self,choice):
  result=self.candidate(choice)
  return {'connected':True,'name':result['name'],'server_version':result['server_version'],'external_ready':bool(result['ingress_path']) or result['url'].startswith('https://')}
 def apply(self,choice):
  choice=self.validate(choice);resolved=self.candidate(choice)
  return self.commit(choice,resolved)
 def commit(self,choice,resolved):
  choice=self.validate(choice)
  with self.lock:
   self.path.parent.mkdir(parents=True,exist_ok=True);temp=self.path.with_suffix('.tmp');temp.write_text(json.dumps(choice));os.chmod(temp,0o600);os.replace(temp,self.path);self.selection=choice;self.cached=resolved;self.cache_until=time.monotonic()+300;self.status_cache=None;self.last_target=(resolved["url"],resolved["ingress_path"])
  return self.public()
 def restore(self,choice):
  with self.lock:
   if choice is None:self.path.unlink(missing_ok=True)
   else:
    temp=self.path.with_suffix('.tmp');temp.write_text(json.dumps(choice));os.chmod(temp,0o600);os.replace(temp,self.path)
   self.selection=copy.deepcopy(choice);self.cached=None;self.cache_until=0;self.status_cache=None;self.last_target=None
 def resolve(self):
  with self.resolve_lock:
   with self.lock:
    choice=copy.deepcopy(self.selection)
    if choice is None:return {'url':self.legacy_url,'health_url':self.legacy_url,'ingress_path':self.legacy_ingress,'name':'기존 연결 설정'}
    if choice['mode']=='manual':return {'url':choice['url'],'health_url':choice['url'],'ingress_path':'','name':'주소 직접 연결'}
    if self.cached is not None and time.monotonic()<self.cache_until:
     if 'error' in self.cached:raise ConnectionError(self.cached['error'])
     return dict(self.cached)
   try:resolved=self.candidate(choice)
   except ConnectionError as error:
    with self.lock:
     if self.selection==choice:self.cached={'error':str(error)};self.cache_until=time.monotonic()+15
    raise
   with self.lock:
    if self.selection==choice:
     self.cached=resolved;self.cache_until=time.monotonic()+300;self.last_target=(resolved['url'],resolved['ingress_path'])
   return dict(resolved)
 def frame_origin(self):
  with self.lock:
   if self.selection is None:url=self.legacy_url
   elif self.selection['mode']=='manual':url=self.selection['url']
   else:url=(self.cached or {}).get('url') or (self.last_target[0] if self.last_target else None)
   if not url:return ''
   parsed=urlsplit(url);return parsed.scheme+'://'+parsed.netloc
 def revision(self):
  with self.lock:raw=[self.selection,self.last_target if self.selection and self.selection['mode']=='auto' else None]
  return hashlib.sha256(json.dumps(raw,sort_keys=True).encode()).hexdigest()[:20]
 def status(self):
  result=self.resolve();url=result['health_url']
  with self.lock:
   if self.status_cache and self.status_cache[0]==url and time.monotonic()-self.status_cache[1]<10:return dict(self.status_cache[2])
  probed=probe_music(url);public={'connected':bool(probed.get('connected')),'checked_at':int(time.time())}
  with self.lock:self.status_cache=(url,time.monotonic(),public)
  return public
