'use strict';
let config,currentRoom,revision,states={},haError=false,checking=false,toastTimer,modeChanging=false,haConnected=false;
const demo={},pending=new Set();
let lastInteraction=Date.now(),homeData=null,homeError=null,lastHomeRead=0,homeReadTask=null;
const $=selector=>document.querySelector(selector);
function toast(text){$('#toast').textContent=text;$('#toast').classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('#toast').classList.remove('show'),3500);}
function room(){if(config?.home.enabled&&currentRoom===HomePanel.HOME_ID)return {id:HomePanel.HOME_ID,name:'홈',cards:[],sensors:[]};return config?.rooms.find(r=>r.id===currentRoom)||config?.rooms[0];}
function mapped(){return !!config&&(config.rooms.some(r=>r.cards.some(c=>c.entity_id)||r.sensors.some(s=>s.entity_id))||config.home.enabled&&[config.home.weather.entity_id,config.home.washer.state_entity,config.home.dryer.state_entity,...config.home.todos.lists.map(l=>l.entity_id)].some(Boolean));}
function textState(entity){if(entity?.entity_id?.startsWith('automation.')&&!haError&&['on','off'].includes(entity.state))return entity.state==='on'?'활성':'비활성';if(haError)return '연결 끊김';if(!entity)return '읽는 중…';return ({on:'켜짐',off:'꺼짐',unavailable:'사용 불가',unknown:'알 수 없음',open:'열림',closed:'닫힘'})[entity.state]||entity.state;}
function sensorState(key,entity){const state=textState(entity);if(['temperature','humidity'].includes(key)&&!haError&&typeof state==='string'&&state.trim()!==''&&Number.isFinite(Number(state))){const value=Number(state).toFixed(key==='temperature'?1:0);return value==='-0.0'?'0.0':value;}return state;}
function fitSensorRow(row){
 if(!row||row.hidden||!row.children.length||!row.clientWidth)return;const count=row.children.length;row.style.setProperty('--sensor-count',count);row.style.setProperty('--sensor-gap',Math.max(1,Math.min(10,24/count))+'px');
 const canvas=document.createElement('canvas'),ctx=canvas.getContext('2d');if(!ctx)return;let scale=1;
 for(const cell of row.children){const copy=cell.querySelector('.sensor-copy');if(!copy)continue;const label=copy.firstElementChild,value=copy.lastElementChild,family=getComputedStyle(copy).fontFamily;ctx.font='400 11px '+family;const a=ctx.measureText(label.textContent).width;ctx.font='500 20px '+family;const b=ctx.measureText(value.textContent).width;scale=Math.min(scale,(cell.clientWidth-2)/(30+Math.max(a,b)));cell.title=label.textContent+' · '+value.textContent;}
 row.style.setProperty('--sensor-scale',Math.max(.01,scale).toFixed(4));
}
function canControl(card){return !!card.control&&/^(light|switch|automation)\./.test(card.entity_id);}
// One frame loop for visible fan cards. Retain angle/velocity across state polls and redraws.
const FanMotion=(()=>{
 const fans=new Map(),media=window.matchMedia('(prefers-reduced-motion: reduce)');let frame=null,last=null;
 const allowed=()=>config?.motion.fan_enabled!==false&&!document.hidden&&!media.matches&&!document.documentElement.classList.contains('no-motion');
 const paint=fan=>fan.path.setAttribute('transform','rotate('+fan.angle.toFixed(4)+' 12 12)');
 function schedule(){if(frame===null&&allowed()&&[...fans.values()].some(f=>f.path.isConnected&&(f.on||f.speed>0))){last=performance.now();frame=requestAnimationFrame(tick);}}
 function tick(now){frame=null;const dt=Math.min(.1,Math.max(0,(now-last)/1000));last=now;let moving=false;
  for(const [key,fan] of fans){if(!fan.path.isConnected){fans.delete(key);continue;}if(!allowed()){fan.speed=0;continue;}
   const target=fan.on?480:0,tau=fan.on?.55:.75,decay=Math.exp(-dt/tau),delta=fan.speed-target;
   fan.angle=(fan.angle+target*dt+delta*tau*(1-decay))%360;fan.speed=target+delta*decay;
   if(!fan.on&&fan.speed<.3)fan.speed=0;paint(fan);moving=moving||fan.on||fan.speed>0;
  }if(moving&&allowed())frame=requestAnimationFrame(tick);
 }
 function refresh(){if(!allowed()){if(frame!==null)cancelAnimationFrame(frame);frame=null;last=null;for(const fan of fans.values())fan.speed=0;}else schedule();}
 function update(svg,key,on){const path=svg?.querySelector('.fan-rotor')||svg?.querySelector('path');if(!path)return;let fan=fans.get(key);if(!fan){fan={path,angle:0,speed:0,on:false};fans.set(key,fan);}fan.path=path;fan.on=!!on;paint(fan);refresh();}
 document.addEventListener('visibilitychange',refresh);media.addEventListener('change',refresh);
 return {update};
})();

function drawRoom(animate=false){
 const selected=room();if(!selected)return;currentRoom=selected.id;$('#room-name').textContent=selected.name;
 const tabs=$('#room-tabs');tabs.replaceChildren();for(const item of [...(config.home.enabled?[{id:HomePanel.HOME_ID,name:'홈'}]:[]),...config.rooms]){const button=document.createElement('button');button.type='button';button.role='tab';button.textContent=item.name;button.dataset.roomId=item.id;button.setAttribute('aria-selected',String(item.id===currentRoom));button.addEventListener('click',()=>{currentRoom=item.id;drawRoom(true);if(currentRoom===HomePanel.HOME_ID)readHomeData().then(renderHome);});tabs.append(button);}fitPanelTabs(tabs);
 const homeSelected=currentRoom===HomePanel.HOME_ID;$('#home-content').hidden=!homeSelected;
 const grid=$('#light-grid');grid.hidden=homeSelected;grid.replaceChildren();
 for(const card of selected.cards.filter(c=>c.visible)){
  const button=document.createElement('button');button.className='device-card';button.dataset.cardId=card.id;button.type='button';
  const top=document.createElement('span');top.className='card-top';const icon=document.createElement('span');icon.className='icon';icon.append(makePanelIcon(card.icon));top.append(icon);
  if(config.display.card_toggles!==false&&(!card.entity_id||canControl(card))){const toggle=document.createElement('span');toggle.className='switch';toggle.append(document.createElement('span'));top.append(toggle);}
  const label=document.createElement('span');label.className='device-label';label.textContent=card.label;const state=document.createElement('span');state.className='device-state';button.append(top,label,state);
  button.addEventListener('click',()=>activate(card));grid.append(button);
 }
 $('#empty-room').hidden=homeSelected||grid.childElementCount>0;
 if(animate){const page=$('#rooms-page');page.classList.remove('enter');void page.offsetWidth;page.classList.add('enter');}
 renderStates();
}
function renderStates(){
 const selected=room();if(!selected)return;
 for(const button of document.querySelectorAll('[data-card-id]')){
  const card=selected.cards.find(c=>c.id===button.dataset.cardId);const entity=states[card.entity_id];const key=currentRoom+':'+card.id;let on=false;
  if(card.entity_id){on=!haError&&entity?.state==='on';button.disabled=pending.has(key)||haError||!canControl(card)||!['on','off'].includes(entity?.state);button.querySelector('.device-state').textContent=pending.has(key)?'명령 전달·상태 확인 중…':textState(entity)+(entity?.unit?' '+entity.unit:'')+(canControl(card)?'':' · 상태 표시');button.title=card.entity_id;}
  else{on=!!demo[key];button.disabled=false;button.querySelector('.device-state').textContent=on?'켜짐 · 미리보기':'꺼짐 · 미리보기';button.title='엔티티 미연결 · 미리보기';}
  button.setAttribute('aria-pressed',String(on));if(card.icon==='fan')FanMotion.update(button.querySelector('.icon svg'),key,on);
 }
 $('#room-status').textContent=currentRoom===HomePanel.HOME_ID?'':selected.cards.some(c=>c.entity_id)?'':'미리보기';
 const sensorRow=$('.sensor-row');sensorRow.replaceChildren();sensorRow.hidden=!config.display.sensors||selected.sensors.length===0;
 for(const sensor of selected.sensors){const entity=states[sensor.entity_id];let format=sensor.format;let value=sensor.entity_id?sensorState(format,entity)+(entity?.unit?' '+entity.unit:''):'미연결';if(format==='window'&&entity&&!haError)value=({on:'열림',off:'닫힘'})[entity.state]||textState(entity);
 const cell=document.createElement('div');cell.dataset.sensorId=sensor.id;const icon=document.createElement('span');icon.className='sensor-icon';icon.append(makePanelIcon(sensor.icon));const text=document.createElement('span'),label=document.createElement('span'),state=document.createElement('strong');text.className='sensor-copy';label.textContent=sensor.label;state.textContent=value;state.className='sensor-text';text.append(label,state);cell.append(icon,text);sensorRow.append(cell);}

 fitSensorRow(sensorRow);
 renderHome();
 const connected=haConnected&&!haError;for(const led of document.querySelectorAll('.status-led'))led.classList.toggle('is-connected',connected);
 $('#mode-label').textContent=haError?'Home Assistant Offline':haConnected?'Home Assistant Connect':mapped()?'Home Assistant Connecting':'미리보기';$('#ha-status').textContent=haError?'연결 오류':mapped()?'상태 수신 중':'엔티티 미연결';
}
async function activate(card){
 const key=currentRoom+':'+card.id;if(pending.has(key))return;
 if(!card.entity_id){demo[key]=!demo[key];renderStates();return;}
 if(!canControl(card)||haError||!['on','off'].includes(states[card.entity_id]?.state))return;
 const roomId=currentRoom;const desired=states[card.entity_id].state==='on'?'off':'on';pending.add(key);renderStates();
 try{const response=await fetch('./api/control',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({room_id:roomId,card_id:card.id,state:desired})});const body=await response.json();if(!response.ok)throw new Error(body.error||'제어 요청 실패');if(body.state)states[card.entity_id]=body;toast(body.confirmed?card.label+' · '+(card.entity_id.startsWith('automation.')?(desired==='on'?'활성화':'비활성화'):(desired==='on'?'켜짐':'꺼짐'))+' 확인':body.message||'명령 전달 후 상태를 확인 중입니다');await readStates();}
 catch(error){toast(error.message);await readStates();}finally{pending.delete(key);renderStates();}
}
function renderHeaderIcon(){const target=document.querySelector('.brand-mark');if(!config.display.header||!config.display.header_icon){target.textContent='⌂';return;}const image=document.createElement('img');image.alt='';image.addEventListener('error',()=>{if(image.parentNode===target){target.textContent='⌂';target.title='아이콘 파일을 읽을 수 없습니다. www 경로를 확인하세요.';}});target.title='';image.src='./api/header-icon?v='+Date.now();target.replaceChildren(image);}
function applyConfig(next){
 const previous=config;config=next;const homeChanged=JSON.stringify(previous?.home)!==JSON.stringify(config.home);if(homeChanged){homeData=null;homeError=null;lastHomeRead=0;}if(config.home.enabled&&(!previous||!previous.home.enabled))currentRoom=HomePanel.HOME_ID;if(!(config.home.enabled&&currentRoom===HomePanel.HOME_ID)&&!config.rooms.some(r=>r.id===currentRoom))currentRoom=config.rooms[0].id;
 if(!previous||config.home.enabled&&!previous.home.enabled||config.home.auto_return&&!previous.home.auto_return)lastInteraction=Date.now();
 const root=document.documentElement;applyPanelTheme(config.theme,config.theme_id);
 const modeToggle=$('#panel-mode-toggle');modeToggle.setAttribute('aria-checked',String(config.color_mode==='dark'));modeToggle.title=config.color_mode==='dark'?'라이트 모드로 전환':'다크 모드로 전환';modeToggle.disabled=modeChanging;
 for(const key of ['radius','gap','cardHeight','fontSize'])root.style.setProperty('--'+key,config.theme[key]+'px');root.style.setProperty('--columns',config.theme.columns);root.style.setProperty('--motion',config.motion.enabled?config.motion.duration+'ms':'0ms');root.style.setProperty('--distance',config.motion.distance+'px');root.classList.toggle('no-motion',!config.motion.enabled);
 renderHeaderIcon();$('#brand-label').textContent=config.brand;$('#page-title').textContent=config.title;$('#page-sub').textContent=config.subtitle;$('header').hidden=!config.display.header;$('.notice').hidden=!config.display.notice;$('.sensor-row').hidden=!config.display.sensors;drawRoom();
}
async function readStates(){if(!mapped()){states={};haError=false;haConnected=false;renderStates();return;}try{const response=await fetch('./api/entity-states',{cache:'no-store'});if(!response.ok)throw new Error('HA 상태 읽기 실패');states=(await response.json()).states;haError=false;haConnected=true;}catch(error){haError=true;haConnected=false;}renderStates();}
async function sync(){if(checking||(document.hidden&&revision!==undefined))return;checking=true;try{const response=await fetch('./api/revision',{cache:'no-store'});if(response.status===401){location.href='./login';return;}if(!response.ok)throw new Error('연결 오류');const next=await response.json();if(next.revision!==revision){const r=await fetch('./api/config',{cache:'no-store'});if(!r.ok)throw new Error('설정 읽기 실패');applyConfig(await r.json());revision=next.revision;}await Promise.all([readStates(),readHomeData()]);renderHome();}catch(error){haError=true;haConnected=false;if(config)renderStates();}finally{checking=false;}}
function renderHome(){if(config?.home.enabled&&currentRoom===HomePanel.HOME_ID)HomePanel.render($('#home-content'),config.home,states,homeData,homeError,haError);}
async function readHomeData(){if(!config?.home.enabled||!config.home.todos.enabled||currentRoom!==HomePanel.HOME_ID||Date.now()-lastHomeRead<30000)return;if(homeReadTask)return homeReadTask;
 const signature=JSON.stringify(config.home);homeReadTask=(async()=>{try{const response=await fetch('./api/home-data',{cache:'no-store'});if(!response.ok)throw new Error('할 일 목록 연결을 확인해 주세요');const data=await response.json();if(signature===JSON.stringify(config.home)){homeData=data;homeError=null;lastHomeRead=Date.now();}}catch(error){homeError=error.message;lastHomeRead=Date.now();}finally{homeReadTask=null;}})();return homeReadTask;
}
function checkHomeReturn(){if(!config)return;if(HomePanel.shouldReturn(config.home,currentRoom,lastInteraction,Date.now(),pending.size>0)){
 currentRoom=HomePanel.HOME_ID;document.querySelectorAll('.page').forEach(page=>{page.hidden=page.id!=='rooms-page';});document.querySelectorAll('[data-page]').forEach(tab=>{tab.classList.toggle('active',tab.dataset.page==='rooms');tab.setAttribute('aria-current',tab.dataset.page==='rooms'?'page':'false');});drawRoom(true);window.scrollTo({top:0,behavior:'auto'});readHomeData().then(renderHome);
 }else if(currentRoom===HomePanel.HOME_ID)renderHome();}
for(const event of ['pointerdown','keydown','wheel','touchmove'])document.addEventListener(event,()=>{lastInteraction=Date.now();},{passive:true});
setInterval(checkHomeReturn,1000);document.addEventListener('visibilitychange',()=>{if(!document.hidden)checkHomeReturn();});
function clock(){const now=new Date();$('#clock').textContent=new Intl.DateTimeFormat('ko-KR',{hour:'2-digit',minute:'2-digit',hour12:false}).format(now);$('#date').textContent=new Intl.DateTimeFormat('ko-KR',{month:'long',day:'numeric',weekday:'short'}).format(now);}
document.querySelectorAll('[data-page]').forEach(button=>button.addEventListener('click',()=>{document.querySelectorAll('.page').forEach(page=>{page.hidden=page.id!==button.dataset.page+'-page';page.classList.remove('enter');});const page=$('#'+button.dataset.page+'-page');void page.offsetWidth;page.classList.add('enter');document.querySelectorAll('[data-page]').forEach(tab=>{tab.classList.toggle('active',tab===button);tab.setAttribute('aria-current',tab===button?'page':'false');});}));
$('#panel-mode-toggle').addEventListener('click',async()=>{if(!config||modeChanging)return;modeChanging=true;$('#panel-mode-toggle').disabled=true;try{const response=await fetch('./api/appearance',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({color_mode:config.color_mode==='dark'?'light':'dark'})});if(!response.ok)throw new Error('화면 모드를 저장하지 못했습니다');const readback=await fetch('./api/config',{cache:'no-store'});if(!readback.ok)throw new Error('모드 저장 후 확인에 실패했습니다');applyConfig(await readback.json());toast(config.color_mode==='dark'?'다크 모드 적용':'라이트 모드 적용');}catch(error){toast(error.message);}finally{modeChanging=false;$('#panel-mode-toggle').disabled=false;}});
window.addEventListener('resize',()=>fitSensorRow($('.sensor-row')));document.fonts?.addEventListener('loadingdone',()=>fitSensorRow($('.sensor-row')));
clock();sync();setInterval(()=>{if(!document.hidden)clock();},30000);setInterval(sync,5000);document.addEventListener('visibilitychange',()=>{if(!document.hidden){clock();sync();}});
