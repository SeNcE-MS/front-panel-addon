"""Small, scoped Music Assistant HTTP bridge. Credentials never leave the server."""
import hashlib,hmac,json,os,re,secrets,threading,time
from pathlib import Path
from music_search import rank_tracks
from urllib.parse import urlsplit
from urllib.request import Request,build_opener,HTTPRedirectHandler

class MusicError(ValueError):pass
READS=frozenset({'players/all','player_queues/all','player_queues/items','music/search','config/providers','music/tracks/get','music/tracks/library_items','music/albums/library_items','music/artists/library_items','music/playlists/library_items','music/albums/album_tracks','music/artists/artist_albums','music/artists/artist_tracks','music/playlists/playlist_tracks'})
WRITES=frozenset({'player_queues/play','player_queues/pause','player_queues/next','player_queues/previous','player_queues/play_index','player_queues/play_media','players/cmd/volume_set'})
class NoRedirect(HTTPRedirectHandler):
 def redirect_request(self,*a,**k):return None
class MusicAPI:
 def __init__(self,directory,base='',token='',load_saved=True):
  self.path=Path(directory)/'music-api-auth.json';self.lock=threading.RLock();self.base=base.rstrip('/');self.token=token;self.connection_url=None;self.target_check=None
  if load_saved and self.path.exists():
   try:
    d=json.loads(self.path.read_text());self.base,self.token=self.validate_auth(d['url'],d['token'])
   except (OSError,ValueError,KeyError,TypeError):self.base=self.token=''
  try:
   if self.base and self.token:self.base,self.token=self.validate_auth(self.base,self.token)
   else:self.base=self.token=''
  except MusicError:self.base=self.token=''
 @staticmethod
 def validate_auth(url,token):
  try:p=urlsplit(url);p.port
  except (ValueError,TypeError):raise MusicError('MA API 주소를 확인해 주세요.') from None
  if not isinstance(url,str) or len(url)>2048 or p.scheme not in ['http','https'] or not p.hostname or p.username is not None or p.password is not None or p.query or p.fragment or re.search(r'[\x00-\x20\\]',url):raise MusicError('MA HTTP(S) API 주소가 필요합니다.')
  if not isinstance(token,str) or not 1<=len(token)<=8192 or re.search(r'[\x00-\x20]',token):raise MusicError('MA 인증 토큰을 확인해 주세요.')
  return url.rstrip('/'),token
 def configured(self):return bool(self.base and self.token)
 def _check_target(self,base):
  if not callable(self.connection_url):return
  target=self.connection_url().rstrip('/')
  if target==base:return
  with self.lock:previous=self.target_check
  if previous and previous[0]==(base,target) and previous[1]>time.monotonic():return
  identities=[]
  for url in [base,target]:
   with build_opener(NoRedirect).open(Request(url+'/info',headers={'Accept':'application/json'}),timeout=4) as r:raw=r.read(65537)
   if len(raw)>65536:raise MusicError('MA 서버 식별 정보 오류')
   info=json.loads(raw);identity=info.get('server_id') if isinstance(info,dict) else None
   if not isinstance(identity,str) or not identity:raise MusicError('MA 서버 식별 정보 오류')
   identities.append(identity)
  if identities[0]!=identities[1]:raise MusicError('선택한 MA 서버와 상세 연동 인증이 다릅니다. HA 웹 UI에서 인증을 다시 연결해 주세요.')
  with self.lock:self.target_check=((base,target),time.monotonic()+60)
 def call(self,command,args):
  if command not in READS|WRITES or not isinstance(args,dict):raise MusicError('허용되지 않은 음악 요청입니다.')
  with self.lock:base,token=self.base,self.token
  if not base or not token:raise MusicError('MA 상세 연동 인증이 필요합니다. HA 웹 UI의 Music Assistant 설정을 확인해 주세요.')
  try:
   self._check_target(base)
   req=Request(base+'/api',data=json.dumps({'command':command,'args':args}).encode(),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json','Accept':'application/json'},method='POST')
   with build_opener(NoRedirect).open(req,timeout=8 if command=='music/tracks/get' else 15) as r:raw=r.read(8388609)
   if len(raw)>8388608:raise MusicError('음악 목록이 너무 큽니다. 더 작은 목록을 선택해 주세요.')
   result=json.loads(raw)
   if isinstance(result,dict) and ('error_code' in result or 'error' in result):raise MusicError('MA가 요청을 처리하지 못했습니다.')
   return result
  except MusicError:raise
  except Exception as e:
   if command in WRITES:raise MusicError('명령 결과가 불확실합니다. 자동 재시도하지 않았습니다. 현재 재생 상태를 확인해 주세요.') from None
   if getattr(e,'code',None) in [401,403]:raise MusicError('MA 상세 연동 인증을 다시 확인해 주세요.') from None
   raise MusicError('MA 데이터를 읽지 못했습니다. 서버 연결을 확인해 주세요.') from None
 def authenticate(self,url,token):
  base,token=self.validate_auth(url,token);candidate=MusicAPI(self.path.parent,base,token,load_saved=False)
  players=candidate.call('players/all',{})
  if not isinstance(players,list) or any(not isinstance(x,dict) or not isinstance(x.get('player_id'),str) for x in players):raise MusicError('MA 플레이어 응답 형식을 확인해 주세요.')
  with self.lock:
   temp=self.path.with_suffix('.tmp');temp.write_text(json.dumps({'url':base,'token':token}));temp.chmod(0o600);os.replace(temp,self.path);self.base,self.token=base,token;self.target_check=None
  return {'configured':True}
 def image(self,proxy_id):
  if not isinstance(proxy_id,str) or not re.fullmatch('[a-f0-9]{64}',proxy_id):raise MusicError('앨범 이미지 식별자 오류')
  with self.lock:base,token=self.base,self.token
  if not self.configured():raise MusicError('MA 상세 연동 인증이 필요합니다.')
  try:
   req=Request(base+'/imageproxy/'+proxy_id+'?size=80&fmt=webp',headers={'Authorization':'Bearer '+token})
   with build_opener(NoRedirect).open(req,timeout=5) as r:data=r.read(524289);mime=r.headers.get_content_type()
   if len(data)>524288 or mime not in ['image/png','image/jpeg','image/webp']:raise MusicError('앨범 이미지 형식 오류')
   return data,mime
  except Exception:raise MusicError('앨범 이미지를 읽지 못했습니다.') from None

class MusicBridge:
 PAGE=25
 def __init__(self,rpc,song_search=None):self.rpc=rpc;self.song_search=song_search;self.lock=threading.RLock();self.cache={};self.items={};self.art={};self.confirmations={};self.last_actions={};self.key=secrets.token_bytes(32);self.search_jobs={};self.search_slots=threading.BoundedSemaphore(2)
 def reset(self):
  with self.lock:self.cache.clear();self.items.clear();self.art.clear();self.confirmations.clear();self.search_jobs.clear()
 def _cached(self,key,seconds,fetch):
  with self.lock:c=self.cache.get(key)
  if c and c[0]>time.monotonic():return c[1]
  value=fetch()
  weight=len(value[0]) if isinstance(value,tuple) and isinstance(value[0],bytes) else len(json.dumps(value,ensure_ascii=False).encode())
  if weight<=4194304:
   with self.lock:
    while self.cache and (len(self.cache)>=64 or sum(x[2] for x in self.cache.values())+weight>8388608):self.cache.pop(next(iter(self.cache)))
    self.cache[key]=(time.monotonic()+seconds,value,weight)
  return value
 def _offset(self,value):
  if type(value) is not int or not 0<=value<=100000:raise MusicError('목록 페이지 오류')
  return value
 def _hash(self,value):return hmac.new(self.key,value.encode(),hashlib.sha256).hexdigest()[:32]
 def _remember(self,raw,queue_id=None):
  if not isinstance(raw,dict):raise MusicError('음악 항목 형식 오류')
  media=raw.get('media_item') or raw;kind=media.get('media_type','track');uri=media.get('uri','');qid=raw.get('queue_item_id') if queue_id else None
  if kind not in ['track','album','artist','playlist','radio'] or not isinstance(uri,str) or not uri or len(uri)>4096:raise MusicError('지원하지 않는 음악 항목입니다.')
  identity=(queue_id+':'+str(qid)) if queue_id else uri;item_id=self._hash(identity)
  image=raw.get('image') or media.get('image');metadata=media.get('metadata') or {}
  if not isinstance(image,dict):image=next((i for i in metadata.get('images',[]) if isinstance(i,dict) and i.get('type')=='thumb'),{})
  proxy=image.get('proxy_id')
  if isinstance(proxy,str) and re.fullmatch('[a-f0-9]{64}',proxy):
   with self.lock:self.art[item_id]=proxy
  value={'uri':uri,'item_id':str(media.get('item_id','')),'provider':str(media.get('provider','')),'type':kind,'queue_id':queue_id,'queue_item_id':qid,'available':media.get('available',True) is not False}
  with self.lock:
   if len(self.items)>=4096:
    old=next(iter(self.items));self.items.pop(old);self.art.pop(old,None)
   self.items[item_id]=(time.monotonic()+1800,value)
  artists=media.get('artists') or [];subtitle=', '.join(str(x.get('name','')) for x in artists if isinstance(x,dict))[:240]
  duration=raw.get('duration',media.get('duration',0));duration=duration if type(duration) in [int,float] and 0<=duration<86400 else 0
  return {'id':item_id,'type':kind,'name':str(media.get('name',raw.get('name','음악')))[:240],'artist':subtitle,'duration':duration,'art_id':item_id if proxy and re.fullmatch('[a-f0-9]{64}',str(proxy)) else None,'available':value['available']}
 def _item(self,item_id):
  if not isinstance(item_id,str) or not re.fullmatch('[a-f0-9]{32}',item_id):raise MusicError('음악 목록을 새로 불러와 주세요.')
  with self.lock:value=self.items.get(item_id)
  if not value or value[0]<time.monotonic():raise MusicError('음악 목록이 만료되었습니다. 다시 불러와 주세요.')
  return value[1]
 def _normalize(self,raw,queue_id=None):
  if not isinstance(raw,list):raise MusicError('MA 목록 형식 오류')
  out=[]
  for x in raw:
   try:out.append(self._remember(x,queue_id))
   except MusicError:continue
  return out
 def library(self,category,offset=0):
  self._offset(offset);kinds={'favorites':'tracks','tracks':'tracks','albums':'albums','artists':'artists','playlists':'playlists'}
  if category not in kinds:raise MusicError('지원하지 않는 음악 목록입니다.')
  args={'limit':self.PAGE+1,'offset':offset,'order_by':'sort_name'}
  if category=='favorites':args['favorite']=True
  raw=self._cached(('library',category,offset),60,lambda:self.rpc.call('music/'+kinds[category]+'/library_items',args))
  rows=self._normalize(raw);return {'items':rows[:self.PAGE],'offset':offset,'has_more':len(raw)>self.PAGE}
 def children(self,item_id,offset=0,view="tracks"):
  self._offset(offset);item=self._item(item_id);commands={'album':'music/albums/album_tracks','artist':'music/artists/artist_albums','playlist':'music/playlists/playlist_tracks'}
  if item['type'] not in commands or item['queue_id'] or view not in ['tracks','albums']:raise MusicError('이 음악 항목은 펼칠 수 없습니다.')
  if item['type']=='artist':commands['artist']='music/artists/artist_albums' if view=='albums' else 'music/artists/artist_tracks'
  raw=self._cached(('children',item_id,view),120,lambda:self.rpc.call(commands[item['type']],{'item_id':item['item_id'],'provider_instance_id_or_domain':item['provider']}))
  if not isinstance(raw,list) or len(raw)>4096:raise MusicError('음악 목록 크기를 확인해 주세요.')
  return {'items':self._normalize(raw[offset:offset+self.PAGE]),'offset':offset,'has_more':len(raw)>offset+self.PAGE}
 def _search_worker(self,query,job):
  try:
   result=self.rpc.call('music/search',{'search_query':query,'media_types':['track'],'limit':50,'library_only':False})
   if not isinstance(result,dict):raise MusicError('검색 응답 형식 오류')
   tracks=list(result.get('tracks') or [])
   if self.song_search is not None and (not tracks or re.search('[가-힣]',query)):
    try:tracks.extend(self.song_search.search(query,self.rpc))
    except Exception:pass
   result=dict(result,tracks=rank_tracks(query,tracks))
   with self.lock:
    if self.search_jobs.get(query) is job:job.update(result=result,pending=False,until=time.monotonic()+90)
  except Exception:
   with self.lock:
    if self.search_jobs.get(query) is job:job.update(result=None,pending=False,error=True,until=time.monotonic()+30)
  finally:self.search_slots.release()
 def search(self,query,offset=0):
  self._offset(offset)
  if not isinstance(query,str) or not 1<=len(query.strip())<=120 or re.search(r'[\x00-\x1f]',query):raise MusicError('검색어를 확인해 주세요.')
  query=query.strip();fast=self._cached(('library-search',query),60,lambda:self.rpc.call('music/search',{'search_query':query,'media_types':['track'],'limit':50,'library_only':True}))
  if not isinstance(fast,dict):raise MusicError('MA 검색 응답 형식 오류')
  with self.lock:
   now=time.monotonic();self.search_jobs={k:v for k,v in self.search_jobs.items() if v.get('pending') or v['until']>now};job=self.search_jobs.get(query)
   if job is None and self.search_slots.acquire(blocking=False):
    while len(self.search_jobs)>=8:
     old=next((k for k,v in self.search_jobs.items() if not v.get('pending')),None)
     if old is None:break
     self.search_jobs.pop(old)
    job={'pending':True,'result':None,'until':now+90};self.search_jobs[query]=job;threading.Thread(target=self._search_worker,args=(query,job),daemon=True).start()
   pending=job is None or job.get('pending',False);raw=(job or {}).get('result') or fast;failed=bool((job or {}).get('error'))
  items=rank_tracks(query,list(raw.get('tracks') or [])+list(fast.get('tracks') or []));return {'items':self._normalize(items[offset:offset+self.PAGE]),'offset':offset,'has_more':len(items)>offset+self.PAGE,'pending':pending,'search_note':'보관함 결과를 먼저 표시했습니다. 전체 서비스 검색 중…' if pending else ('전체 서비스 검색에 실패해 보관함 결과만 표시합니다.' if failed else '')}
 def _players_queues(self,fresh=False):
  if fresh:
   with self.lock:self.cache.pop('players',None);self.cache.pop('queues',None)
  players=self._cached('players',3,lambda:self.rpc.call('players/all',{}));queues=self._cached('queues',3,lambda:self.rpc.call('player_queues/all',{}))
  if not isinstance(players,list) or not isinstance(queues,list):raise MusicError('MA 플레이어 응답 형식 오류')
  return [x for x in players if isinstance(x,dict) and isinstance(x.get('player_id'),str) and x.get('enabled',True) and x.get('hide_in_ui') is not True and x.get('hide_player_in_ui') is not True],{x['queue_id']:x for x in queues if isinstance(x,dict) and isinstance(x.get('queue_id'),str)}
 def _player(self,player_id,fresh=False):
  players,queues=self._players_queues(fresh);player=next((x for x in players if x['player_id']==player_id),None)
  if not player or not player.get('available'):raise MusicError('사용 가능한 MA 스피커를 선택해 주세요.')
  qid=next((k for k in [player.get('active_group'),player.get('active_source'),player_id] if isinstance(k,str) and k in queues),None)
  if qid is None:raise MusicError('선택한 스피커의 대기열을 찾지 못했습니다.')
  return player,queues[qid]
 def snapshot(self,player_id=''):
  players,queues=self._players_queues();out={'players':[{'id':p['player_id'],'name':str(p.get('display_name') or p.get('name','스피커'))[:160],'available':bool(p.get('available'))} for p in players],'selected':None}
  if player_id:
   p,q=self._player(player_id);now=q.get('current_item');volume=p.get('volume_level');volume=volume if type(volume) in [int,float] and 0<=volume<=100 else None
   out['selected']={'id':p['player_id'],'name':str(p.get('display_name') or p.get('name','스피커'))[:160],'state':str(q.get('state',p.get('state','idle'))),'volume':volume,'can_volume':'volume_set' in (p.get('supported_features') or []),'queue_count':int(q.get('items') or 0),'can_queue_next':self._next_allowed(q),'index':q.get('current_index'),'elapsed':q.get('elapsed_time') or 0,'current':self._remember(now,q['queue_id']) if isinstance(now,dict) and now.get('media_item') else None}
  return out
 def queue(self,player_id,offset=0):
  self._offset(offset);_,q=self._player(player_id);raw=self._cached(('queue',q['queue_id'],offset),3,lambda:self.rpc.call('player_queues/items',{'queue_id':q['queue_id'],'offset':offset,'limit':self.PAGE+1}));rows=self._normalize(raw,q['queue_id']);return {'items':rows[:self.PAGE],'offset':offset,'has_more':len(raw)>self.PAGE,'total':int(q.get('items') or 0),'index':q.get('current_index')}
 def image(self,item_id):
  self._item(item_id)
  with self.lock:proxy=self.art.get(item_id)
  if not proxy:raise MusicError('앨범 이미지 없음')
  return self._cached(('image',proxy),300,lambda:self.rpc.image(proxy))
 @staticmethod
 def _next_allowed(queue):
  index=queue.get('current_index');buffer=queue.get('index_in_buffer')
  return bool(queue.get('items')) and not queue.get('ended',False) and type(index) is int and index>=0 and (buffer is None or (type(buffer) is int and buffer<=index))
 @classmethod
 def _require_next(cls,queue):
  if not cls._next_allowed(queue):raise MusicError('현재 곡이 없거나 MA가 다음 곡을 이미 미리 불러왔습니다. 현재 곡 바로 뒤에 넣을 수 없어 대기열을 변경하지 않았습니다.')
 def confirm(self,player_id,item_id,mode,actor):
  if mode not in ['play','append','next']:raise MusicError('음악 재생 방식 오류')
  _,queue=self._player(player_id,True);item=self._item(item_id)
  if mode=='next':
   self._require_next(queue)
   if item['type']!='track':raise MusicError('다음곡으로 대기는 개별 곡만 지원합니다.')
  if item['queue_id'] or not item['available'] or item['type'] not in ['track','album','artist','playlist','radio']:raise MusicError('재생할 수 없는 음악입니다.')
  token=secrets.token_urlsafe(32)
  with self.lock:
   now=time.monotonic();self.confirmations={k:v for k,v in self.confirmations.items() if v[0]>now}
   if len(self.confirmations)>=128:self.confirmations.pop(next(iter(self.confirmations)))
   self.confirmations[token]=(now+30,actor,player_id,item_id,mode)
  return {'confirmation':token,'expires_in':30}
 def action(self,body,actor):
  if not isinstance(body,dict) or not isinstance(body.get('action'),str) or not isinstance(body.get('player_id'),str):raise MusicError('음악 명령 형식 오류')
  action=body['action'];fields={'play':set(),'pause':set(),'next':set(),'previous':set(),'volume':{'volume'},'play_item':{'item_id','confirmation'},'append_item':{'item_id','confirmation'},'next_item':{'item_id','confirmation'},'queue_play':{'item_id'}}
  if action not in fields or set(body)!={'action','player_id'}|fields[action]:raise MusicError('허용되지 않은 음악 명령입니다.')
  if action=='volume' and (type(body['volume']) is not int or not 0<=body['volume']<=100):raise MusicError('볼륨은 0~100 사이 정수여야 합니다.')
  item=None
  if action in ['play_item','append_item','next_item','queue_play']:item=self._item(body['item_id'])
  if action in ['play_item','append_item','next_item']:
   mode={'play_item':'play','append_item':'append','next_item':'next'}[action];token=body['confirmation']
   if not isinstance(token,str):raise MusicError('재생 전 확인이 필요합니다.')
   with self.lock:value=self.confirmations.pop(token,None)
   if not value or value[0]<time.monotonic() or value[1:]!=(actor,body['player_id'],body['item_id'],mode):raise MusicError('재생 전 확인이 필요합니다.')
   if item['queue_id'] or not item['available']:raise MusicError('재생할 수 없는 음악입니다.')
  player,queue=self._player(body['player_id'],True)
  if action=='next_item':
   self._require_next(queue)
   if item['type']!='track':raise MusicError('다음곡으로 대기는 개별 곡만 지원합니다.')
  if action=='volume':
   if 'volume_set' not in (player.get('supported_features') or []):raise MusicError('이 스피커는 볼륨 조절을 지원하지 않습니다.')
   command='players/cmd/volume_set';args={'player_id':player['player_id'],'volume_level':body['volume']}
  elif action in ['play_item','append_item','next_item']:
   command='player_queues/play_media';args={'queue_id':queue['queue_id'],'media':item['uri'],'option':{'play_item':'replace','append_item':'add','next_item':'next'}[action],'radio_mode':False}
  elif action=='queue_play':
   if item['queue_id']!=queue['queue_id'] or not isinstance(item['queue_item_id'],str):raise MusicError('선택한 스피커의 대기열 항목이 아닙니다.')
   command='player_queues/play_index';args={'queue_id':queue['queue_id'],'index':item['queue_item_id']}
  else:
   if not queue.get('items'):raise MusicError('재생 대기열이 비어 있습니다.')
   command='player_queues/'+action;args={'queue_id':queue['queue_id']}
  with self.lock:
   now=time.monotonic()
   if self.last_actions.get(player['player_id'],0)>now-.5:
    error=MusicError('상태 확인 후 다시 눌러 주세요.');error.status=429;raise error
   self.last_actions[player['player_id']]=now
  try:self.rpc.call(command,args)
  finally:
   with self.lock:
    self.cache.pop('players',None);self.cache.pop('queues',None)
    for key in list(self.cache):
     if isinstance(key,tuple) and key[0]=='queue':self.cache.pop(key,None)
  return {'accepted':True,'message':'명령을 전달했습니다. 실제 재생 상태를 확인해 주세요.'}
