"""Bounded public audio discovery; every displayed candidate is resolved by the selected MA server.
No audio downloads, account cookies, new login, or playback commands are used here.
"""
import concurrent.futures as futures
import hashlib,json,re,threading,time,unicodedata
from itertools import zip_longest
from urllib.parse import urlencode
from urllib.request import Request,urlopen

def normalized(value):
 return re.sub(r'[^a-z0-9가-힣]','',unicodedata.normalize('NFKC',str(value or '')).casefold())

def rank_tracks(query,items):
 """Title/explicit-artist relevance, Korean-language preference, then official recordings.
 Hangul is a language signal, not a claim about an artist's nationality.
 """
 needle=normalized(query);korean=bool(re.search('[가-힣]',query));unique=[];seen=set();recordings=set()
 for row in items:
  if not isinstance(row,dict) or row.get('media_type','track')!='track' or not row.get('uri'):continue
  keys={row['uri']}|{str(m.get('provider_domain'))+':'+str(m.get('item_id')) for m in row.get('provider_mappings',[]) if isinstance(m,dict) and m.get('provider_domain') and m.get('item_id')}
  duration=row.get('duration');recording=(normalized(row.get('name')),tuple(normalized(a.get('name')) for a in row.get('artists',[]) if isinstance(a,dict)),normalized(row.get('version')),duration)
  if keys&seen or (duration and recording in recordings):continue
  seen.update(keys);recordings.add(recording);unique.append(row)
 def key(row):
  title=normalized(row.get('name'));artists=' '.join(str(a.get('name','')) for a in row.get('artists',[]) if isinstance(a,dict));artist=normalized(artists);remaining=needle;artist_hit=False
  for part in re.findall('[가-힣]+|[a-z0-9]+',unicodedata.normalize('NFKC',artists).casefold()):
   if len(part)>=2 and part not in ['the','and'] and part in remaining and part not in title:remaining=remaining.replace(part,'');artist_hit=True
  tail=needle.replace(title,'',1) if title and title in needle else ''
  if len(tail)>=2 and tail in artist:remaining=title;artist_hit=True
  match=3 if remaining and remaining==title else 2 if remaining and remaining in title else 0
  if not match and needle in normalized(row.get('_search_title')):match=2
  language=(2 if re.search('[가-힣]',artists) else 1 if re.search('[가-힣]',str(row.get('name',''))) else 0) if korean else 0
  version=str(row.get('version',''))+' '+str(row.get('name',''));noise=bool(re.search(r'\b(?:cover|karaoke|instrumental|remix|live|fancam)\b|커버|노래방|직캠|리믹스',version,re.I)) and not any(x in query.casefold() for x in ['cover','karaoke','instrumental','remix','live','fancam','커버','노래방','직캠','리믹스'])
  return (-match,-int(artist_hit),-language,int(noise),-int(bool(row.get('_search_official'))))
 return sorted(unique,key=key)

class QuietLogger:
 def debug(self,*a,**k):pass
 def warning(self,*a,**k):pass
 def error(self,*a,**k):pass

class SongSearch:
 """Search only auto-generated official audio channels, not arbitrary videos.
 MA provider discovery and full track resolution are READs; no library additions or metadata refreshes.
 """
 def __init__(self):self.lock=threading.RLock();self.cache={}
 def cached(self,key,seconds,fetch):
  with self.lock:old=self.cache.get(key)
  if old and old[0]>time.monotonic():return old[1]
  value=fetch()
  with self.lock:
   while len(self.cache)>=256:self.cache.pop(next(iter(self.cache)))
   self.cache[key]=(time.monotonic()+seconds,value)
  return value
 def suggestions(self,query):
  if not re.fullmatch('[가-힣]{2,4}',query):return []
  try:
   url='https://suggestqueries.google.com/complete/search?'+urlencode({'client':'firefox','ds':'yt','hl':'ko','q':query})
   with urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=4) as r:raw=r.read(65537)
   if len(raw)>65536:return []
   rows=json.loads(raw)[1]
   return list(dict.fromkeys(x for x in rows if isinstance(x,str) and 2<=len(x)<=80 and normalized(x).startswith(normalized(query)) and normalized(x)!=normalized(query)))[:4]
  except Exception:return []
 def candidates(self,query):
  from yt_dlp import YoutubeDL
  opts={'quiet':True,'no_warnings':True,'logger':QuietLogger(),'extract_flat':True,'skip_download':True,'socket_timeout':8,'retries':0,'extractor_retries':0,'cachedir':False,'geo_bypass':False}
  try:
   with YoutubeDL(opts) as y:data=y.extract_info('ytsearch20:'+query,download=False)
   return [r for r in (data or {}).get('entries',[]) if isinstance(r,dict) and re.fullmatch(r'[A-Za-z0-9_-]{11}',str(r.get('id',''))) and str(r.get('channel','')).endswith(' - Topic') and isinstance(r.get('duration'),(float,int)) and 30<=r['duration']<=1200][:12]
  except Exception:return []
 def search(self,query,rpc):
  # Separate metadata caches when credentials or the selected MA server change.
  scope=(id(rpc),getattr(rpc,'base',''),hashlib.sha256(str(getattr(rpc,'token','')).encode()).hexdigest())
  providers=self.cached(('providers',scope),60,lambda:rpc.call('config/providers',{'provider_domain':'ytmusic','include_values':False}))
  provider=next((p.get('instance_id') for p in providers if isinstance(p,dict) and p.get('domain')=='ytmusic' and p.get('enabled') is True and p.get('status')=='loaded'),None) if isinstance(providers,list) else None
  if not provider:return []
  queries=[query]+self.cached(('suggest',query),300,lambda:self.suggestions(query));groups=[]
  with futures.ThreadPoolExecutor(max_workers=3) as pool:
   groups=list(pool.map(lambda q:self.cached(('public',q),300,lambda:self.candidates(q)),queries))
  # Round-robin expansions: don't let the first completion crowd out other matching song titles.
  candidates=[];seen=set()
  for batch in zip_longest(*groups):
   for row in batch:
    if row and row['id'] not in seen:seen.add(row['id']);candidates.append(row)
  candidates=candidates[:8]
  def resolve(row):
   try:
    media=self.cached(('track',scope,provider,row['id']),600,lambda:rpc.call('music/tracks/get',{'item_id':row['id'],'provider_instance_id_or_domain':provider,'allow_update_metadata':False}))
    if not isinstance(media,dict) or media.get('media_type')!='track' or not media.get('uri') or not media.get('artists') or media.get('available') is False:return None
    mappings=media.get('provider_mappings') or []
    if mappings and not any(m.get('available',True) for m in mappings if isinstance(m,dict)):return None
    return dict(media,_search_official=True,_search_title=row.get('title',''))
   except Exception:return None
  with futures.ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(resolve,candidates))
  return rank_tracks(query,[r for r in rows if r])
