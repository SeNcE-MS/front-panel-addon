'use strict';
(function(root){
const HOME_ID='@home';
function shouldReturn(home,current,last,now,busy){return !!home?.enabled&&!!home.auto_return&&current!==HOME_ID&&!busy&&now-last>=300000;}
function isActive(settings,states,error){return !!settings?.enabled&&!error&&settings.active_states.includes(states[settings.state_entity]?.state);}
function remaining(entity,now=Date.now()){
 if(!entity||['unknown','unavailable',''].includes(entity.state))return '시간 확인 중';
 let minutes;const value=entity.state;
 if(entity.attributes?.device_class==='timestamp'||/^\d{4}-\d\d-\d\dT/.test(value)){const end=Date.parse(value);if(!Number.isFinite(end))return '시간 확인 중';minutes=Math.ceil((end-now)/60000);}
 else{if(typeof value!=='string'||!value.trim()||!Number.isFinite(Number(value)))return '시간 확인 중';const n=Number(value),unit=entity.unit;minutes=['min','minutes','minute'].includes(unit)?Math.ceil(n):['s','seconds','second'].includes(unit)?Math.ceil(n/60):['h','hours','hour'].includes(unit)?Math.ceil(n*60):undefined;}
 if(!Number.isFinite(minutes))return '시간 확인 중';if(minutes<=0)return '마무리 중';
 return minutes>=60?Math.floor(minutes/60)+'시간 '+String(minutes%60).padStart(2,'0')+'분':minutes+'분';
}
const conditions={'clear-night':'맑은 밤',cloudy:'흐림',exceptional:'기상 특보',fog:'안개',hail:'우박',lightning:'뇌우','lightning-rainy':'뇌우와 비',partlycloudy:'구름 조금',pouring:'강한 비',rainy:'비',snowy:'눈','snowy-rainy':'진눈깨비',sunny:'맑음',windy:'바람','windy-variant':'흐리고 바람'};
function el(tag,cls,text){const node=document.createElement(tag);if(cls)node.className=cls;if(text!==undefined)node.textContent=text;return node;}
function svg(path,cls){const ns='http://www.w3.org/2000/svg',node=document.createElementNS(ns,'svg');node.setAttribute('viewBox','0 0 24 24');node.setAttribute('fill','none');node.setAttribute('stroke','currentColor');node.setAttribute('stroke-width','1.5');node.setAttribute('stroke-linecap','round');node.setAttribute('stroke-linejoin','round');node.setAttribute('aria-hidden','true');if(cls)node.setAttribute('class',cls);const p=document.createElementNS(ns,'path');p.setAttribute('d',path);node.append(p);return node;}
function weatherKind(state,text=''){
 if((!state||['unknown','unavailable'].includes(state))&&/(확인|연결)/.test(text))return 'unknown';
 if(['lightning','lightning-rainy'].includes(state)||/번개|뇌우/.test(text))return 'storm';
 if(/진눈깨비/.test(text)||/눈/.test(text)&&/비/.test(text)||state==='snowy-rainy')return 'mixed';if(/눈/.test(text)||state==='snowy')return 'snow';if(/비/.test(text)||['rainy','pouring','lightning-rainy'].includes(state))return 'rain';
 return ({sunny:'sun','clear-night':'night',partlycloudy:'partly',cloudy:'cloud',fog:'fog',windy:'wind','windy-variant':'wind',lightning:'storm',hail:'snow'})[state]||'cloud';
}
function weatherIcon(kind){
 const cloud='M13 31h22a8 8 0 0 0 .3-16A12 12 0 0 0 13 13a9 9 0 0 0 0 18Z';
 const paths={sun:'M24 14a10 10 0 1 0 0 20 10 10 0 0 0 0-20ZM24 4v4m0 32v4M4 24h4m32 0h4M10 10l3 3m22 22 3 3M10 38l3-3m22-22 3-3',night:'M25.8 6A16.8 16.8 0 1 0 38.8 31.9A16.6 16.6 0 0 1 25.8 6ZM15 8v4m-2-2h4m21 5v4m-2-2h4',cloud,
 partly:'M14 0v3M2 12h3M5 3l2 2M23 3l-2 2M26 12h3'+cloud,
 rain:cloud+'M15 36l-2 5m12-5-2 5m12-5-2 5',snow:cloud+'M14 36v8m-3-6 6 4m0-4-6 4m23-6v8m-3-6 6 4m0-4-6 4',mixed:cloud+'M15 36l-2 5m20-5v8m-3-6 6 4m0-4-6 4',fog:cloud+'M9 37h30M13 42h22',wind:'M5 17h26a6 6 0 1 0-6-6M5 24h33a4 4 0 1 1-4 4M5 31h15a6 6 0 1 1-6 6',storm:cloud+'m25 33-6 7h8l-5 7',unknown:'M24 5a19 19 0 1 0 0 38 19 19 0 0 0 0-38ZM18 18a6 6 0 1 1 10 4c-4 2-4 4-4 7m0 7h.01'};
 const icon=svg(paths[kind]||paths.unknown,'weather-symbol');icon.setAttribute('viewBox','0 0 48 48');icon.setAttribute('stroke-width','1.1');
 const layers=[];const layer=(path,cls)=>layers.push([path,cls]);
 if(kind==='sun'){layer(paths.sun.split('M24 4')[0],'weather-disc');layer('M24 4'+paths.sun.split('M24 4')[1],'weather-rays');}
 else if(kind==='night'){layer(paths.night.split('M15 8')[0],'weather-moon');layer('M15 8'+paths.night.split('M15 8')[1],'weather-stars');}
 else if(['rain','snow','mixed','fog','storm'].includes(kind)){layer(paths[kind].slice(cloud.length),'weather-'+kind+'-detail');layer(cloud,'weather-cloud');}
 else if(kind==='partly'){layer(paths.partly.slice(0,-cloud.length),'weather-partly-sun');layer(cloud,'weather-cloud');}
 else layer(paths[kind]||paths.unknown,kind==='cloud'?'weather-cloud':kind==='wind'?'weather-wind':'weather-static');
 icon.replaceChildren();for(const [path,cls] of layers){const group=document.createElementNS('http://www.w3.org/2000/svg','g');group.setAttribute('class',cls);group.append(svg(path).firstChild);if(cls==='weather-partly-sun'){const disc=document.createElementNS('http://www.w3.org/2000/svg','circle');for(const [key,value] of Object.entries({cx:14,cy:12,r:8,fill:'var(--weather-sun)',stroke:'none'}))disc.setAttribute(key,value);group.prepend(disc);}if(cls==='weather-mixed-detail'){group.firstChild.setAttribute('d','M15 36l-2 5');group.append(svg('M33 36v8m-3-6 6 4m0-4-6 4').firstChild);}icon.append(group);}return icon;
}
function renderWeather(home,states,error){
 const settings=home.weather,bindings=settings.sensors||{},entity=states[settings.entity_id],attrs=entity?.attributes||{};
 const state=key=>{const v=states[bindings[key]]?.state;return !error&&typeof v==='string'&&v.trim()&&!['unknown','unavailable'].includes(v)?v:undefined;};
 const number=(key,fallback)=>{const v=state(key);return v!==undefined&&Number.isFinite(Number(v))?Number(v):!error&&typeof fallback==='number'&&Number.isFinite(fallback)?fallback:undefined;};
 const fmt=(value,digits=1)=>value===undefined?'—':String(Number(value.toFixed(digits)));const temp=value=>fmt(value,settings.temperature_decimals===0?0:1);const condition=state('condition')||(!error&&entity?conditions[entity.state]||'상태 확인':'연결 확인');
 const kind=weatherKind(error?'unknown':entity?.state,condition),card=el('article','home-card home-large weather-card');card.dataset.homeCard='weather';card.dataset.weatherKind=kind;
 const head=el('div','home-card-head'),location=el('div','weather-location');location.append(el('small','home-muted','NAVER WEATHER · 오늘'),el('h2',null,state('location')||entity?.name?.replace(/^Naver Weather /,'').split(' 날씨 ')[0]||'날씨'));head.append(location,el('span','home-chip','현재 날씨'));
 const body=el('div','home-hero weather-hero'),copy=el('div','weather-reading');const values=el('div','weather-values'),humidity=el('div','weather-humidity');humidity.append(el('strong','weather-humidity-value',fmt(number('humidity',bindings.humidity?undefined:attrs.humidity),0)+'%'));values.append(el('strong','home-big weather-temperature',temp(number('temperature',attrs.temperature))+'°'));if(settings.show_humidity!==false)values.append(humidity);copy.append(values);
 const range=el('div','weather-range');range.append(el('span','weather-high','최고 '+temp(number('high'))+'°'),el('span','weather-low','최저 '+temp(number('low'))+'°'));copy.append(range);
 const scene=el('div','weather-scene'),orb=el('div','weather-orb');orb.append(weatherIcon(kind));scene.append(orb,el('strong','weather-condition',condition));body.append(copy,scene);
 const metrics=el('div','weather-metrics');for(const [key,label,fallback,unit] of [['pm10','미세먼지',undefined,'μg/m³'],['pm25','초미세먼지',undefined,'μg/m³'],['precipitation_probability','강수확률',undefined,'%'],['wind','바람',attrs.wind_speed,attrs.wind_speed_unit||'']]){
 const box=el('div','weather-metric');box.dataset.weatherMetric=key;const title=el('span','metric-label',label);let value=number(key,fallback);if(key==='precipitation_probability'){title.classList.add('metric-label-icon');title.prepend(svg('M3 12a9 9 0 0 1 18 0H3Zm9 0v7a2 2 0 0 0 4 0M12 2v1','precipitation-icon'));if(value!==undefined&&(value<0||value>100))value=undefined;}box.append(title,el('strong',null,key==='precipitation_probability'?(value===undefined?'—':String(Math.round(value))):fmt(value)),el('small','home-muted',key==='precipitation_probability'?'%':states[bindings[key]]?.unit||unit));metrics.append(box);}
 card.append(head,body,metrics);return card;
}

function completionTime(entity,now){
 if(!entity||typeof entity.state!=='string'||!entity.state.trim()||['unknown','unavailable'].includes(entity.state))return '확인 중';
 let end;if(entity.attributes?.device_class==='timestamp'||/^\d{4}-\d\d-\d\dT/.test(entity.state))end=Date.parse(entity.state);else{const factor=({min:60000,minutes:60000,minute:60000,s:1000,seconds:1000,second:1000,h:3600000,hours:3600000,hour:3600000})[entity.unit];if(factor&&Number.isFinite(Number(entity.state)))end=now+Number(entity.state)*factor;}
 if(!Number.isFinite(end))return '확인 중';if(end<=now)return '갱신 대기';const date=new Date(end),today=new Date(now),clock=new Intl.DateTimeFormat('ko-KR',{hour:'2-digit',minute:'2-digit',hour12:false}).format(date);
 if(date.toDateString()===today.toDateString())return clock;const tomorrow=new Date(today);tomorrow.setDate(tomorrow.getDate()+1);return (date.toDateString()===tomorrow.toDateString()?'내일':new Intl.DateTimeFormat('ko-KR',{month:'numeric',day:'numeric'}).format(date))+' '+clock;
}
function laundryMachine(kind){
 const image=svg('M24 5h72a9 9 0 0 1 9 9v120a9 9 0 0 1-9 9H24a9 9 0 0 1-9-9V14a9 9 0 0 1 9-9ZM15 36h90M28 18h23v7H28v-7Zm51-2a5 5 0 1 0 0 10 5 5 0 0 0 0-10ZM60 51a37 37 0 1 0 0 74 37 37 0 0 0 0-74ZM27 143v3m66-3v3','laundry-machine');image.setAttribute('viewBox','0 0 120 150');image.setAttribute('stroke-width','2');
 const ns='http://www.w3.org/2000/svg',rotor=document.createElementNS(ns,'g');rotor.setAttribute('class','laundry-drum');rotor.append(svg('M60 61a27 27 0 0 1 24 15M87 88a27 27 0 0 1-15 24M60 115a27 27 0 0 1-24-15M33 88a27 27 0 0 1 15-24','').firstChild);image.append(rotor);
 const detail=svg(kind==='washer'?'M38 91c8-9 14 9 22 0s14 9 22 0M39 101c7-7 14 7 21 0s14 7 21 0':'M48 100c-8-9 8-13 0-23m12 23c-8-9 8-13 0-23m12 23c-8-9 8-13 0-23','').firstChild;detail.setAttribute('class','laundry-detail');image.append(detail);return image;
}
function renderLaundry(key,label,settings,states,now){
 const card=el('article','home-card home-large laundry-card');card.dataset.homeCard=key;
 const state=states[settings.state_entity]?.state,phase=({detecting:'무게 감지 중',rinsing:'헹굼 중',spinning:'탈수 중',soaking:'불림 중',frozen_prevent_running:'동결 방지 중',detergent_amount:'세제 양 확인 중',drying:'건조 중',cooling:'식히는 중',prewash:'예비 세탁 중',dispensing:'세제 투입 중',steam_softening:'스팀 중',add_drain:'배수 중',refreshing:'리프레시 중'})[state]||(key==='washer'?'세탁 중':'건조 중');
 const head=el('div','home-card-head laundry-head'),name=el('h2','laundry-name',label),status=el('span','laundry-status');status.append(el('i','laundry-status-dot'),document.createTextNode('작동 중'));head.append(name,status);
 const body=el('div','laundry-body'),copy=el('div','laundry-copy'),time=remaining(states[settings.remaining_entity],now),line=el('div','laundry-time');line.append(el('strong','home-big laundry-remaining',time));if(time.endsWith('분'))line.append(el('span','laundry-suffix','남았습니다.'));copy.append(line);
 const visual=el('div','laundry-visual');visual.append(laundryMachine(key));body.append(copy,visual);
 const foot=el('div','laundry-footer'),activity=el('div','laundry-activity'),bars=el('span','laundry-bars');bars.setAttribute('aria-hidden','true');for(let i=0;i<3;i++)bars.append(el('i'));activity.append(bars,el('span','laundry-phase',phase));const finish=el('div','laundry-finish');finish.append(el('span',null,'완료 예상'),el('strong',null,completionTime(states[settings.remaining_entity],now)));foot.append(activity,finish);card.append(head,body,foot);return card;
}
function fitLaundryTimes(target){
 if(typeof document==='undefined'||!target)return;const canvas=document.createElement('canvas'),ctx=canvas.getContext('2d');if(!ctx)return;
 for(const copy of target.querySelectorAll('.laundry-copy')){const node=copy.querySelector('.laundry-remaining');if(!node||!copy.clientWidth)continue;const css=getComputedStyle(node),limit=window.innerWidth<=460?56:88,suffix=copy.querySelector('.laundry-suffix'),line=copy.querySelector('.laundry-time'),reserve=suffix?suffix.getBoundingClientRect().width+(parseFloat(getComputedStyle(line).columnGap)||0):0;ctx.font=css.fontWeight+' '+limit+'px '+css.fontFamily;const spacing=parseFloat(css.letterSpacing)||0,width=ctx.measureText(node.textContent).width+spacing*Math.max(0,node.textContent.length-1),size=Math.min(limit,Math.floor(limit*(copy.clientWidth-reserve-4)/width));node.style.setProperty('--laundry-time-size',Math.max(12,size)+'px');}
}
if(typeof window!=='undefined'&&typeof document!=='undefined'){window.addEventListener('resize',()=>fitLaundryTimes(document));document.fonts?.ready.then(()=>fitLaundryTimes(document));document.fonts?.addEventListener('loadingdone',()=>fitLaundryTimes(document));}
const rendered=new WeakMap();
function render(target,home,states,data,error,haError,now=Date.now()){
 target.dataset.iconAnimation=String(home.icon_animation!==false);
 const stamp=JSON.stringify([home,states,data,error,haError,Math.floor(now/60000)]);if(rendered.get(target)===stamp)return;rendered.set(target,stamp);
 target.replaceChildren();let cards=0;
 for(const [key,label] of [['washer','세탁기'],['dryer','건조기']]){
  const settings=home[key];if(!isActive(settings,states,haError))continue;
  target.append(renderLaundry(key,label,settings,states,now));cards++;
 }
 if(home.weather.enabled){target.append(renderWeather(home,states,haError));cards++;}
 if(home.todos.enabled){const group=el('article','home-card todo-group'),title=el('div','home-card-head');title.append(el('h2',null,'할 일 목록'),el('span','home-muted','진행 중인 항목'));group.append(title);for(const list of home.todos.lists){
  const found=data?.todos?.find(item=>item.entity_id===list.entity_id),items=found?.items||[],label=states[list.entity_id]?.name||list.entity_id||'미연결';
  const card=el('div','todo-section');card.dataset.todoLabel=label;const head=el('div','home-card-head');head.append(el('h2',null,label),el('span','home-chip',found&&!found.error&&!error?items.length+'개 진행 중':'상태 확인'));card.append(head);
  if(error||found?.error||!found){card.append(el('p','home-muted',error||found?.error||'목록을 읽고 있습니다…'));}
  else if(!items.length){card.append(el('p','home-muted','진행 중인 항목이 없습니다.'));}
  else{const ul=el('ul','home-tasks');for(const item of items){const li=el('li');li.append(el('span','task-dot','○'),el('span',null,item.summary));if(item.due)li.append(el('small','home-muted',item.due));ul.append(li);}card.append(ul);}
  group.append(card);
 }target.append(group);cards++;}
 if(haError)target.append(el('p','home-muted','HA 상태 연결을 확인해 주세요. 세탁·건조 작동 여부를 확인할 수 없습니다.'));
 if(!cards)target.append(el('p','home-muted','홈 카드 표시가 꺼져 있거나 작동 중인 기기가 없습니다.'));
 fitLaundryTimes(target);
}
const api={HOME_ID,shouldReturn,isActive,remaining,render};if(typeof module==='object'&&module.exports)module.exports=api;else root.HomePanel=api;
})(typeof window==='undefined'?globalThis:window);
