"""Fixed, capability-aware HA controls. No arbitrary targets, services or payloads."""
import math
ACTION_DOMAINS=frozenset('fan climate cover lock media_player vacuum humidifier scene script button input_button input_boolean'.split())
READ_ONLY_DOMAINS=frozenset({'sensor','binary_sensor'})
CONTROL_ATTRIBUTES=frozenset('supported_features percentage percentage_step oscillating direction preset_mode preset_modes current_temperature temperature target_temp_low target_temp_high target_temp_step min_temp max_temp hvac_modes hvac_action fan_mode fan_modes swing_mode swing_modes swing_horizontal_mode swing_horizontal_modes humidity current_humidity min_humidity max_humidity mode available_modes current_position current_tilt_position code_format volume_level is_volume_muted source source_list sound_mode sound_mode_list shuffle repeat media_title media_artist fan_speed fan_speed_list battery_level'.split())

def safe_attributes(attrs):
 out={}
 for key in CONTROL_ATTRIBUTES:
  value=attrs.get(key)
  if isinstance(value,str):out[key]=value[:160]
  elif isinstance(value,bool):out[key]=value
  elif isinstance(value,(int,float)) and math.isfinite(value):out[key]=value
  elif isinstance(value,list):out[key]=[v[:160] for v in value[:64] if isinstance(v,str) and v]
 return out

def describe(state,services,motor=None,angle=None):
 domain=state['entity_id'].split('.')[0];attrs=state.get('attributes') or {};actions=[]
 result={'state':state,'actions':actions,'note':''}
 if domain not in ACTION_DOMAINS:return result
 if state['state']=='unavailable' or state['state']=='unknown' and domain not in {'scene','button','input_button'}:
  result['note']='기기 상태를 확인할 수 없어 제어를 표시하지 않습니다.';return result
 features=attrs.get('supported_features',0);features=features if type(features) is int and 0<=features<2**32 else 0
 available=services.get(domain,set())
 def add(action,label,fields=None,bit=None,confirm=False):
  if action in available and (bit is None or features&bit):actions.append({'id':action,'label':label,'fields':fields or [],'confirm':confirm})
 def number(name,label,low,high,step=1,attribute=None,scale=1):
  return {'name':name,'label':label,'type':'number','min':low,'max':high,'step':step,'value':attrs.get(attribute or name),'scale':scale}
 def enumeration(action,label,param,options,bit=None,attribute=None):
  if not isinstance(options,list):return
  labels=({'off':'끄기','cool':'냉방','heat':'난방','heat_cool':'냉난방','auto':'자동','dry':'제습','fan_only':'송풍'} if param=='hvac_mode' else {'forward':'정방향','reverse':'역방향'} if param=='direction' else {'off':'반복 없음','all':'전체 반복','one':'한 곡 반복'} if param=='repeat' else {})
  choices=[{'value':v,'label':labels.get(v,v)} for v in options[:64] if isinstance(v,str) and 0<len(v)<=160]
  if choices:add(action,label,[{'name':param,'label':label,'type':'select','options':choices,'value':state['state'] if param=='hvac_mode' else attrs.get(attribute or param)}],bit)
 def boolean(action,label,param,attribute,bit=None):
  add(action,label,[{'name':param,'label':label,'type':'select','options':[{'value':True,'label':'켜기'},{'value':False,'label':'끄기'}],'value':attrs.get(attribute)}],bit)
 def bounds(lowkey,highkey):
  lo,hi=attrs.get(lowkey),attrs.get(highkey)
  return (lo,hi) if type(lo) in (int,float) and type(hi) in (int,float) and math.isfinite(lo) and math.isfinite(hi) and lo<hi else None
 if domain=='fan':
  add('turn_on','켜기',bit=32);add('turn_off','끄기',bit=16)
  step=attrs.get('percentage_step',1);step=step if type(step) in (int,float) and 0<step<=100 else 1
  add('set_percentage','속도 · %',[number('percentage','속도 · %',0,100,step)],1)
  boolean('oscillate','좌우 회전','oscillating','oscillating',2)
  enumeration('set_direction','회전 방향','direction',['forward','reverse'],4)
  enumeration('set_preset_mode','프리셋','preset_mode',attrs.get('preset_modes'),8)
  if isinstance(motor,dict) and motor.get('state') not in {'unknown','unavailable'} and {'LEFT','RIGHT'}<=set(motor.get('options',[])) and 'select_option' in services.get('select',set()):
   for direction,label in [('left','왼쪽'),('right','오른쪽')]:actions.append({'id':'nudge_'+direction,'label':label,'fields':[],'confirm':False})
  if isinstance(angle,dict) and angle.get('state') not in {'unknown','unavailable'} and 'select_option' in services.get('select',set()):
   choices=[{'value':v,'label':v+'°'} for v in angle.get('options',[]) if isinstance(v,str) and v.isascii() and v.isdigit() and 0<int(v)<=360][:32]
   if choices:actions.append({'id':'set_oscillation_angle','label':'회전 각도','fields':[{'name':'option','label':'회전 각도','type':'select','options':choices,'value':angle.get('state')}],'confirm':False})
 elif domain=='climate':
  add('turn_on','켜기',bit=256);add('turn_off','끄기',bit=128)
  enumeration('set_hvac_mode','운전 모드','hvac_mode',attrs.get('hvac_modes'))
  limits=bounds('min_temp','max_temp');step=attrs.get('target_temp_step',.5);step=step if type(step) in (int,float) and 0<step<=10 else .5
  if limits:
   if features&2:add('set_temperature','목표 온도 범위',[number('target_temp_low','하한 온도',*limits,step),number('target_temp_high','상한 온도',*limits,step)],2)
   else:add('set_temperature','목표 온도',[number('temperature','목표 온도',*limits,step)],1)
  limits=bounds('min_humidity','max_humidity')
  if limits and 0<=limits[0]<limits[1]<=100:add('set_humidity','목표 습도 · %',[number('humidity','목표 습도 · %',*limits)],4)
  for action,label,param,bit in [('set_fan_mode','풍량','fan_mode',8),('set_preset_mode','프리셋','preset_mode',16),('set_swing_mode','상하 바람','swing_mode',32),('set_swing_horizontal_mode','좌우 바람','swing_horizontal_mode',512)]:enumeration(action,label,param,attrs.get(param+'s'),bit)
 elif domain=='cover':
  for action,label,bit in [('open_cover','열기',1),('close_cover','닫기',2),('stop_cover','정지',8),('open_cover_tilt','날개 열기',16),('close_cover_tilt','날개 닫기',32),('stop_cover_tilt','날개 정지',64)]:add(action,label,bit=bit,confirm=action in {'open_cover','close_cover'} and attrs.get('device_class') in {'garage','gate','door'})
  add('set_cover_position','열림 정도 · %',[number('position','열림 정도 · %',0,100,attribute='current_position')],4)
  add('set_cover_tilt_position','날개 각도 · %',[number('tilt_position','날개 각도 · %',0,100,attribute='current_tilt_position')],128)
  if attrs.get('device_class') in {'garage','gate','door'}:
   for control in actions:
    if not control['id'].startswith('stop_'):control['confirm']=True
 elif domain=='lock':
  if attrs.get('code_format'):result['note']='PIN이 필요한 잠금장치는 Home Assistant에서 제어해 주세요.'
  elif state['state'] in {'locked','unlocked'}:
   add('lock','잠그기',confirm=True);add('unlock','잠금 해제',confirm=True)
  else:result['note']='잠금장치가 동작 중이거나 상태 확인이 필요합니다.'
 elif domain=='media_player':
  for action,label,bit in [('turn_on','켜기',128),('turn_off','끄기',256),('media_play','재생',16384),('media_pause','일시정지',1),('media_stop','정지',4096),('media_previous_track','이전 곡',16),('media_next_track','다음 곡',32)]:add(action,label,bit=bit)
  add('volume_set','음량 · %',[number('volume_level','음량 · %',0,1,.01,scale=100)],4)
  boolean('volume_mute','음소거','is_volume_muted','is_volume_muted',8)
  enumeration('select_source','입력 소스','source',attrs.get('source_list'),2048)
  enumeration('select_sound_mode','음장 모드','sound_mode',attrs.get('sound_mode_list'),65536)
  boolean('shuffle_set','셔플','shuffle','shuffle',32768);enumeration('repeat_set','반복','repeat',['off','all','one'],262144)
 elif domain=='vacuum':
  for action,label,bit in [('start','청소 시작',8192),('pause','일시정지',4),('stop','청소 정지',8),('return_to_base','충전기로 복귀',16),('locate','위치 알림',512)]:add(action,label,bit=bit)
  enumeration('set_fan_speed','흡입력','fan_speed',attrs.get('fan_speed_list'),32)
 elif domain=='humidifier':
  add('turn_on','켜기');add('turn_off','끄기');limits=bounds('min_humidity','max_humidity')
  if limits and 0<=limits[0]<limits[1]<=100:add('set_humidity','목표 습도 · %',[number('humidity','목표 습도 · %',*limits)])
  enumeration('set_mode','운전 모드','mode',attrs.get('available_modes'),1)
 elif domain=='input_boolean':add('turn_on','켜기');add('turn_off','끄기')
 elif domain in {'scene','script'}:add('turn_on','장면 적용' if domain=='scene' else '스크립트 실행',confirm=True)
 elif domain in {'button','input_button'}:add('press','버튼 실행',confirm=True)
 return result

def validate_action(state,services,action,params,motor=None,angle=None):
 if not isinstance(action,str) or not isinstance(params,dict):raise ValueError('제어 요청 형식 오류')
 control=next((a for a in describe(state,services,motor,angle)['actions'] if a['id']==action),None)
 if control is None:raise ValueError('기기가 지원하지 않는 제어입니다')
 if set(params)!={f['name'] for f in control['fields']}:raise ValueError('제어 항목 오류')
 for field in control['fields']:
  value=params[field['name']]
  if field['type']=='number':
   if type(value) not in (int,float) or not math.isfinite(value) or not field['min']<=value<=field['max']:raise ValueError('조절 범위 오류')
   if field['name'] in {'position','tilt_position'} and int(value)!=value:raise ValueError('위치는 정수로 입력해 주세요')
  elif not any(type(value) is type(o['value']) and value==o['value'] for o in field['options']):raise ValueError('선택 항목 오류')
 if 'target_temp_low' in params and params['target_temp_low']>params['target_temp_high']:raise ValueError('하한 온도는 상한 온도 이하여야 합니다')
 return dict(params)
