"""Optional home-tab settings; no appliance or task mutation capability."""
import copy
from ha_bridge import ID
ACTIVE_STATES=['running','detecting','soaking','drying','dispensing','steam_softening','rinsing','add_drain','prewash','refreshing','spinning','detergent_amount','frozen_prevent_running','cooling']
WEATHER_SENSORS={key:'' for key in ['temperature','high','low','pm10','pm25','condition','wind','location','humidity','precipitation_probability']}
HOME_DEFAULT={'icon_animation':True,'enabled':False,'auto_return':False,'weather':{'enabled':True,'entity_id':'','temperature_decimals':1,'show_humidity':True,'sensors':WEATHER_SENSORS},'washer':{'enabled':True,'state_entity':'','remaining_entity':'','active_states':ACTIVE_STATES},'dryer':{'enabled':True,'state_entity':'','remaining_entity':'','active_states':ACTIVE_STATES},'todos':{'enabled':True,'lists':[{'label':label,'entity_id':''} for label in ['할 일 1','할 일 2','할 일 3','할 일 4']]}}

def validate_home(raw):
 h=copy.deepcopy(raw)
 if isinstance(h,dict):h.setdefault('icon_animation',True)
 if isinstance(h,dict) and isinstance(h.get('weather'),dict):
  h['weather'].setdefault('temperature_decimals',1)
  h['weather'].setdefault('show_humidity',True)
  sensors=h['weather'].setdefault('sensors',copy.deepcopy(WEATHER_SENSORS))
  if isinstance(sensors,dict):sensors.setdefault('humidity','');sensors.setdefault('precipitation_probability','')
 if not isinstance(h,dict) or set(h)!=set(HOME_DEFAULT):raise ValueError('홈 설정 항목 오류')
 def entity(value,domain=None):
  return isinstance(value,str) and len(value)<=160 and (not value or bool(ID.fullmatch(value)) and (domain is None or value.split('.')[0] in domain))
 for key in ['enabled','auto_return','icon_animation']:
  if type(h[key]) is not bool:raise ValueError('홈 체크 설정 오류')
 for key in ['weather','washer','dryer','todos']:
  section=h[key]
  if not isinstance(section,dict) or set(section)!=set(HOME_DEFAULT[key]) or type(section['enabled']) is not bool:raise ValueError('홈 카드 설정 오류')
  if key=='weather':
   if type(section['show_humidity']) is not bool:raise ValueError('습도 표시 설정 오류')
   if type(section['temperature_decimals']) is not int or section['temperature_decimals'] not in (0,1):raise ValueError('기온 소수점 설정 오류')
   if not entity(section['entity_id'],{'weather'}):raise ValueError('날씨 엔티티 오류')
   if not isinstance(section['sensors'],dict) or set(section['sensors'])!=set(WEATHER_SENSORS) or any(not entity(eid,{'sensor'}) for eid in section['sensors'].values()):raise ValueError('날씨 상세 센서 오류')
  elif key in ['washer','dryer']:
   if any(not entity(section[field],{'sensor','binary_sensor'}) for field in ['state_entity','remaining_entity']):raise ValueError('세탁·건조 상태 센서 오류')
   values=section['active_states']
   if not isinstance(values,list) or not 1<=len(values)<=32 or any(not isinstance(v,str) or not 1<=len(v)<=64 or v in ['unknown','unavailable',''] for v in values):raise ValueError('작동 상태 목록 오류')
  else:
   if not isinstance(section['lists'],list) or not 0<=len(section['lists'])<=16:raise ValueError('할 일 목록은 16개까지 가능합니다')
   for item in section['lists']:
    if not isinstance(item,dict) or set(item)!={'label','entity_id'} or not isinstance(item['label'],str) or len(item['label'])>160 or not entity(item['entity_id'],{'todo'}):raise ValueError('할 일 연결 오류')
 return h

def home_ids(h):
 if not h['enabled']:return set()
 ids=set()
 if h['weather']['enabled']:ids.update([h['weather']['entity_id'],*h['weather']['sensors'].values()])
 for key in ['washer','dryer']:
  if h[key]['enabled']:ids.update(h[key][field] for field in ['state_entity','remaining_entity'])
 if h['todos']['enabled']:ids.update(item['entity_id'] for item in h['todos']['lists'])
 return ids-{''}
