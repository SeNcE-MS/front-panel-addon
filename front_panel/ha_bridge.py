"""Scoped HA bridge. Token never leaves the add-on server."""
import json,re,threading,time
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from concurrent.futures import ThreadPoolExecutor

ID=re.compile(r'[a-z_]+\.[a-z0-9_]+')
CONTROL_DOMAINS=frozenset({'light','switch','automation'})
class HAReadError(Exception):pass

class HAClient:
    def __init__(self,token,base='http://supervisor/core/api'):
        self.token=token;self.base=base.rstrip('/');self.lock=threading.RLock();self.cache={}
    def _get(self,path):
        if not self.token:raise HAReadError('HA 연결 토큰을 사용할 수 없습니다')
        try:
            req=Request(self.base+path,headers={'Authorization':'Bearer '+self.token,'Accept':'application/json'},method='GET')
            with urlopen(req,timeout=8) as response:return json.load(response)
        except HTTPError as error:
            if error.code==404:return None
            raise HAReadError(f'HA 읽기 실패 (HTTP {error.code})') from None
        except (URLError,ValueError,TimeoutError,OSError):raise HAReadError('HA 연결을 확인해 주세요') from None
    @staticmethod
    def slim(state):
        attrs=state.get('attributes') or {};eid=state['entity_id']
        extra={key:attrs[key] for key in ['temperature','temperature_unit','humidity','wind_speed','wind_speed_unit','device_class'] if key in attrs and isinstance(attrs[key],(str,int,float)) and not isinstance(attrs[key],bool)}
        return {'entity_id':eid,'name':str(attrs.get('friendly_name',eid))[:160],'domain':eid.split('.')[0],'state':str(state.get('state','unknown'))[:160],'unit':str(attrs.get('unit_of_measurement',''))[:24],'attributes':extra}
    def catalog(self):
        with self.lock:
            cached=self.cache.get('catalog')
            if cached and cached[0]>time.monotonic()-15:return cached[1]
        raw=self._get('/states')
        if not isinstance(raw,list):raise HAReadError('HA 엔티티 목록 형식 오류')
        result=sorted([self.slim(item) for item in raw if isinstance(item,dict) and ID.fullmatch(str(item.get('entity_id','')))],key=lambda item:(item['domain'],item['name'].casefold()))
        with self.lock:self.cache['catalog']=(time.monotonic(),result)
        return result
    def _state(self,eid):
        if not ID.fullmatch(eid):raise HAReadError('엔티티 ID 오류')
        with self.lock:
            cached=self.cache.get(eid)
            if cached and cached[0]>time.monotonic()-4:return eid,cached[1]
        raw=self._get('/states/'+eid)
        state=self.slim(raw) if isinstance(raw,dict) else {'entity_id':eid,'name':eid,'domain':eid.split('.')[0],'state':'unavailable','unit':''}
        with self.lock:self.cache[eid]=(time.monotonic(),state)
        return eid,state
    def set_state(self,eid,state):
        if not ID.fullmatch(eid) or eid.split('.')[0] not in CONTROL_DOMAINS or state not in ['on','off']:
            raise HAReadError('허용하지 않은 기기 제어입니다')
        with self.lock:self.cache.pop(eid,None)
        _,before=self._state(eid)
        if before['state'] not in ['on','off']:raise HAReadError('기기가 사용 불가 상태여서 제어하지 않았습니다')
        domain=eid.split('.')[0]
        payload={'entity_id':eid}
        if domain=='automation' and state=='off':payload['stop_actions']=False
        request=Request(self.base+'/services/'+domain+'/turn_'+state,data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+self.token,'Content-Type':'application/json'},method='POST')
        try:
            with urlopen(request,timeout=8) as response:response.read()
        except HTTPError as error:raise HAReadError(f'HA 제어 요청 실패 (HTTP {error.code})') from None
        except (URLError,TimeoutError,OSError):raise HAReadError('명령 전달 결과가 불확실합니다. 다시 누르기 전에 현재 상태를 확인해 주세요') from None
        observed=None
        for attempt in range(4):
            try:
                with self.lock:self.cache.pop(eid,None)
                _,observed=self._state(eid)
                if observed['state']==state:return {**observed,'confirmed':True}
            except HAReadError:break
            time.sleep(.3)
        return {'entity_id':eid,'state':observed['state'] if observed else 'unknown','confirmed':False,'message':'명령은 전달했지만 아직 변경 상태가 확인되지 않았습니다'}

    def todo_items(self,eid):
        """Read incomplete items only; never expose arbitrary services or task writes."""
        if not isinstance(eid,str) or not ID.fullmatch(eid) or not eid.startswith('todo.'):raise HAReadError('할 일 엔티티 오류')
        if not self.token:raise HAReadError('HA 연결 토큰을 사용할 수 없습니다')
        key='todo:'+eid
        with self.lock:
            cached=self.cache.get(key)
            if cached and cached[0]>time.monotonic()-30:return cached[1]
        request=Request(self.base+'/services/todo/get_items?return_response',data=json.dumps({'entity_id':eid,'status':'needs_action'}).encode(),headers={'Authorization':'Bearer '+self.token,'Content-Type':'application/json'},method='POST')
        try:
            with urlopen(request,timeout=8) as response:raw=json.load(response)
            items=raw['service_response'][eid]['items']
            if not isinstance(items,list):raise ValueError('items')
            result=[{'summary':str(item.get('summary',''))[:500],'due':str(item.get('due',''))[:128]} for item in items if isinstance(item,dict) and item.get('status')=='needs_action'][:100]
        except (HTTPError,URLError,ValueError,KeyError,TypeError,TimeoutError,OSError):raise HAReadError('할 일 목록을 읽지 못했습니다') from None
        with self.lock:self.cache[key]=(time.monotonic(),result)
        return result

    def states(self,ids):
        if not ids:return {}
        with ThreadPoolExecutor(max_workers=4) as pool:return dict(pool.map(self._state,sorted(ids)))
