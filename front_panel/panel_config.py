"""Validated panel configuration, presets and lossless v3 migration."""
import copy,re
from header_icon import validate_icon_path
from ha_bridge import ID
from home_config import HOME_DEFAULT,validate_home,home_ids
from theme_palettes import PALETTES,TOKEN_COLORS,preset
COLORS=('background','surface','text','muted','accent','active')
EMPTY_SENSORS={'temperature':'','humidity':'','window':''}
ICONS={'lightbulb':'전구','power':'전원','toggle':'스위치','lamp':'스탠드','plug':'콘센트','fan':'선풍기','ceiling':'천장등','desk':'책상','monitor':'모니터','coffee':'커피','aircon':'에어컨','water':'물','thermometer':'온도','humidity':'습도','window':'창문','door':'문','star':'별','home':'집','curtain':'커튼','blinds':'블라인드','led-strip':'LED 스트립','downlight':'다운라이트','mdi:motion-sensor':'재실 센서'}
THEME_DEFAULT={**preset('navy'),'radius':25,'gap':16,'columns':2,'cardHeight':190,'fontSize':16}
BASE_CARDS=[{'id':key,'label':label,'icon':icon,'entity_id':'','visible':True,'control':True} for key,label,icon in [('main','메인 조명','lightbulb'),('indirect','간접 조명','lamp'),('floor','스탠드','plug')]]
DEFAULT={'title':'편안한 우리 집','subtitle':'자주 쓰는 공간을 한눈에.','brand':'우리 집','theme_id':'navy','color_mode':'dark','theme':THEME_DEFAULT,'motion':{'enabled':True,'fan_enabled':True,'duration':200,'distance':9},'display':{'header':True,'sensors':True,'notice':True,'header_icon':'','card_toggles':True},'rooms':[{'id':'room-'+str(i),'name':name,'cards':copy.deepcopy(BASE_CARDS),'sensors':copy.deepcopy(EMPTY_SENSORS)} for i,name in enumerate(['거실','침실','주방'])]}

DEFAULT['home']=copy.deepcopy(HOME_DEFAULT)

def migrate(raw):
 if not isinstance(raw,dict):raise ValueError('설정 형식 오류')
 if 'rooms' in raw:
  out=copy.deepcopy(raw);
  if isinstance(out.get('motion'),dict):out['motion'].setdefault('fan_enabled',True)
  if isinstance(out.get('display'),dict):out['display'].setdefault('header_icon','');out['display'].setdefault('card_toggles',True)
  out.setdefault('home',copy.deepcopy(HOME_DEFAULT));common=out.pop('sensors',None)
  if common is not None and (not isinstance(common,dict) or set(common)!=set(EMPTY_SENSORS)):raise ValueError('이전 센서 형식 오류')
  if isinstance(out['rooms'],list):
   for index,room in enumerate(out['rooms']):
    if isinstance(room,dict) and 'sensors' not in room:room['sensors']=copy.deepcopy(common if index==0 and common is not None else EMPTY_SENSORS)
  if isinstance(out.get('theme'),dict):
   out.setdefault('color_mode',out['theme'].get('mode','dark' if out.get('theme_id')=='navy' else 'light'))
   for key,value in preset('navy').items():out['theme'].setdefault(key,value)
  return out
 if not all(k in raw for k in ['title','subtitle','brand','theme','motion','display','cards']):raise ValueError('설정 형식 오류')
 out=copy.deepcopy(DEFAULT)
 for key in ['title','subtitle','brand','theme','motion','display']:out[key]=copy.deepcopy(raw[key])
 bindings=raw.get('bindings',{'rooms':{name:{} for name in ['거실','침실','주방']},'sensors':EMPTY_SENSORS})
 out['rooms'][0]['sensors']=copy.deepcopy(bindings['sensors'])
 for room in out['rooms']:
  room['cards']=[]
  for card in raw['cards']:
   if card['id']=='all-off':continue
   item=copy.deepcopy(next((x for x in BASE_CARDS if x['id']==card['id']),BASE_CARDS[0]));item.update({k:card[k] for k in ['id','label','visible']})
   item['entity_id']=bindings['rooms'].get(room['name'],{}).get(card['id'],'');item['control']=item['entity_id'].split('.')[0] in ['light','switch'] if item['entity_id'] else True
   room['cards'].append(item)
 return migrate(out)

def validate(raw):
 c=migrate(raw)
 if set(c)!=set(DEFAULT):raise ValueError('설정 항목 오류')
 c['home']=validate_home(c['home'])
 for key in ['title','subtitle','brand']:
  if not isinstance(c[key],str) or not 1<=len(c[key])<=80:raise ValueError('문구는 1~80자입니다')
 if c['theme_id'] not in PALETTES:raise ValueError('테마 오류')
 if not isinstance(c['color_mode'],str) or c['color_mode'] not in ['light','dark']:raise ValueError('화면 모드 오류')
 if not isinstance(c['theme'],dict) or set(c['theme'])!=set(THEME_DEFAULT):raise ValueError('화면 설정 오류')
 for key in (*COLORS,*TOKEN_COLORS):
  if not isinstance(c['theme'][key],str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',c['theme'][key]):raise ValueError('색상 형식 오류')
 if c['theme']['mode'] not in ['dark','light']:raise ValueError('밝기 모드 오류')
 c['theme'].update(preset(c['theme_id'],c['color_mode']))
 for key,lo,hi in [('radius',0,48),('gap',4,40),('columns',1,3),('cardHeight',110,300),('fontSize',12,24)]:
  if type(c['theme'][key]) is not int or not lo<=c['theme'][key]<=hi:raise ValueError('화면 크기 범위 오류')
 if not isinstance(c['motion'],dict) or set(c['motion'])!=set(DEFAULT['motion']) or any(type(c['motion'][key]) is not bool for key in ['enabled','fan_enabled']):raise ValueError('애니메이션 설정 오류')
 for key,hi in [('duration',800),('distance',30)]:
  if type(c['motion'][key]) is not int or not 0<=c['motion'][key]<=hi:raise ValueError('애니메이션 범위 오류')
 if not isinstance(c['display'],dict) or set(c['display'])!=set(DEFAULT['display']) or any(type(c['display'][key]) is not bool for key in ['header','sensors','notice','card_toggles']):raise ValueError('표시 설정 오류')
 validate_icon_path(c['display']['header_icon'])
 if not isinstance(c['rooms'],list) or not 1<=len(c['rooms'])<=16:raise ValueError('방은 1~16개까지 가능합니다')
 room_ids=set();total=0
 def valid_id(value):return isinstance(value,str) and bool(re.fullmatch(r'[A-Za-z0-9_-]{1,64}',value))
 def entity(value):return isinstance(value,str) and len(value)<=160 and (not value or bool(ID.fullmatch(value)))
 for room in c['rooms']:
  if not isinstance(room,dict) or set(room)!={'id','name','cards','sensors'} or not valid_id(room['id']) or room['id'] in room_ids:raise ValueError('방 ID 오류')
  sensors=room['sensors']
  if isinstance(sensors,dict):
   if set(sensors)!=set(EMPTY_SENSORS) or any(not entity(eid) for eid in sensors.values()):raise ValueError('방 센서 연결 오류')
   sensors=[{'id':key,'label':label,'icon':icon,'entity_id':sensors[key],'format':key} for key,label,icon in [('temperature','실내 온도','thermometer'),('humidity','습도','humidity'),('window','창문','window')]]
   room['sensors']=sensors
  if not isinstance(sensors,list) or len(sensors)>16:raise ValueError('방 센서 항목은 0~16개입니다')
  sensor_ids=set()
  for item in sensors:
   if not isinstance(item,dict) or set(item)!={'id','label','icon','entity_id','format'}:raise ValueError('센서 항목 형식 오류')
   if not valid_id(item['id']) or item['id'] in sensor_ids:raise ValueError('센서 ID 오류')
   sensor_ids.add(item['id'])
   if not isinstance(item['label'],str) or not 1<=len(item['label'])<=40 or item['icon'] not in ICONS:raise ValueError('센서 이름/아이콘 오류')
   if not entity(item['entity_id']) or item['format'] not in ['auto','temperature','humidity','window']:raise ValueError('센서 연결/표시 형식 오류')
  room_ids.add(room['id'])
  if not isinstance(room['name'],str) or not 1<=len(room['name'])<=30:raise ValueError('방 이름 오류')
  if not isinstance(room['cards'],list) or len(room['cards'])>32:raise ValueError('방당 카드는 32개 이하입니다')
  total+=len(room['cards']);card_ids=set()
  for card in room['cards']:
   if not isinstance(card,dict) or set(card)!={'id','label','icon','entity_id','visible','control'}:raise ValueError('카드 형식 오류')
   if not valid_id(card['id']) or card['id'] in card_ids:raise ValueError('카드 ID 오류')
   card_ids.add(card['id'])
   if not isinstance(card['label'],str) or not 1<=len(card['label'])<=40 or card['icon'] not in ICONS:raise ValueError('카드 이름/아이콘 오류')
   if not entity(card['entity_id']) or type(card['visible']) is not bool or type(card['control']) is not bool:raise ValueError('카드 연결 오류')
 if total>128:raise ValueError('전체 카드는 128개 이하입니다')

 return c

def selected_ids(config):return {eid for room in config['rooms'] for eid in [*[card['entity_id'] for card in room['cards']],*[item['entity_id'] for item in room['sensors']]] if eid}|home_ids(config['home'])
def meta():return {'home_default':copy.deepcopy(HOME_DEFAULT),'themes':[{'id':key,'name':value[0],'modes':{mode:preset(key,mode) for mode in ['light','dark']}} for key,value in PALETTES.items()],'icons':[{'id':key,'name':name} for key,name in ICONS.items()]}
