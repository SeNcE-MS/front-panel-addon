'use strict';
// mdi:motion-sensor: Templarian/MaterialDesign, Apache-2.0; see mdi-LICENSE.txt.
window.applyPanelTheme=function(theme,themeId=''){const root=document.documentElement;root.dataset.theme=themeId;for(const [key,css] of Object.entries({background:'bg',surface:'surface',text:'text',muted:'muted',accent:'accent',active:'active',line:'line',onActive:'on-active',onAccent:'on-accent',switchOn:'switch-on',switchOff:'switch-off',thumb:'thumb',soft:'soft',iconBgOff:'icon-bg-off',iconBgOn:'icon-bg-on',iconOff:'icon-off',iconOn:'icon-on',activeBorder:'active-border',hover:'hover'})){if(/^#[0-9a-fA-F]{6}$/.test(theme[key]))root.style.setProperty('--'+css,theme[key]);}root.dataset.mode=theme.mode==='light'?'light':'dark';root.style.colorScheme=root.dataset.mode;};
window.PanelIcons={
 'mdi:motion-sensor':'M10,0.2C9,0.2 8.2,1 8.2,2C8.2,3 9,3.8 10,3.8C11,3.8 11.8,3 11.8,2C11.8,1 11,0.2 10,0.2M15.67,1A7.33,7.33 0 0,0 23,8.33V7A6,6 0 0,1 17,1H15.67M18.33,1C18.33,3.58 20.42,5.67 23,5.67V4.33C21.16,4.33 19.67,2.84 19.67,1H18.33M21,1A2,2 0 0,0 23,3V1H21M7.92,4.03C7.75,4.03 7.58,4.06 7.42,4.11L2,5.8V11H3.8V7.33L5.91,6.67L2,22H3.8L6.67,13.89L9,17V22H10.8V15.59L8.31,11.05L9.04,8.18L10.12,10H15V8.2H11.38L9.38,4.87C9.08,4.37 8.54,4.03 7.92,4.03Z',
 lightbulb:'M9 18h6m-5 3h4M8 13a6 6 0 1 1 8 0c-1 1-1 2-1 3H9c0-1 0-2-1-3Z',
 power:'M12 3v9m-5-7a8 8 0 1 0 10 0',
 toggle:'M8 6h8a6 6 0 0 1 0 12H8A6 6 0 0 1 8 6Zm8 3a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z',
 lamp:'M8 3h8l3 10H5L8 3Zm4 10v8m-4 0h8',
 plug:'M8 3v5m8-5v5M6 8h12v4a6 6 0 0 1-12 0V8Zm6 10v4',
 fan:'M10.7 10.5C8.5 8.5 8.7 4.1 11.3 3.2C13.8 2.3 15.7 3.6 15.4 5.9C15.1 8 13.5 9.4 12.8 10.5Z',
 ceiling:'M12 2v4M8 6h8l5 9H3l5-9Zm2 12h4',
 desk:'M3 10h18v3H3v-3Zm2 3v8m14-8v8M7 7h10',
 monitor:'M3 3h18v14H3V3Zm9 14v4m-5 0h10',
 coffee:'M4 5h13v10a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5V5Zm13 1h2a3 3 0 0 1 0 6h-2M7 2v1m4-1v1',
 aircon:'M3 4h18v10H3V4Zm3 6h12M8 17v4m4-4v3m4-3v4',
 water:'M12 2C9 7 4 11 4 15a8 8 0 0 0 16 0c0-4-5-8-8-13Zm-4 13a4 4 0 0 0 4 4',
 thermometer:'M9 14V5a3 3 0 0 1 6 0v9a5 5 0 1 1-6 0Zm3-7v11',
 humidity:'M12 2C9 7 5 11 5 15a7 7 0 0 0 14 0c0-4-4-8-7-13ZM9 17l6-6m-6 0h.1m5.9 6h.1',
 window:'M3 3h18v18H3V3Zm9 0v18M3 12h18',
 door:'M5 21V3h14v18M3 21h18m-7-9h1',
 star:'m12 2 3 6 7 1-5 5 1 7-6-3-6 3 1-7-5-5 7-1 3-6Z',
 downlight:'M3 7h18v4H3V7Zm3 4 2 3h8l2-3m-6 6v4m-6-5-2 3m14-3 2 3',
 'led-strip':'M4 3h12a6 6 0 0 1 0 12H8a2 2 0 0 0 0 4h12v4H8a6 6 0 0 1 0-12h8a2 2 0 0 0 0-4H4V3Zm3 2h.01m4 0h.01m4 0h.01M20 9h.01M16 13h.01m-4 0h.01m-4 0h.01M4 17h.01M8 21h.01m4 0h.01m4 0h.01',
 curtain:'M3 4h18M4 4v17h6V4m4 0v17h6V4M7 5v13m10-13v13M4 15h6m4 0h6',
 blinds:'M4 3h16v17H4V3Zm0 4h16M4 11h16M4 15h16m3-8v16m-1-1h2',
 home:'m3 10 9-8 9 8v11h-6v-7H9v7H3V10Z'
};
window.fitPanelTabs=function(parent){if(!parent||!parent.children.length)return;const buttons=[...parent.children];for(const button of buttons){button.title=button.textContent;button.setAttribute('aria-label',button.textContent);}for(let font=15;font>=10;font--){parent.style.setProperty('--tab-font',font+'px');parent.style.setProperty('--tab-pad',Math.max(3,(font-10)*3)+'px');parent.style.setProperty('--tab-gap',font<=12?'3px':'6px');if(buttons.every(button=>button.scrollWidth<=button.clientWidth+1))break;}};
if(typeof document!=='undefined'){const fit=()=>document.querySelectorAll('.room-tabs,.editor-room-tabs').forEach(window.fitPanelTabs);window.addEventListener('resize',fit);document.fonts?.ready.then(fit);}
window.makePanelIcon=function(name){const ns='http://www.w3.org/2000/svg';const svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('fill','none');svg.setAttribute('stroke','currentColor');svg.setAttribute('stroke-width','1.7');svg.setAttribute('stroke-linecap','round');svg.setAttribute('stroke-linejoin','round');svg.setAttribute('aria-hidden','true');if(name==='mdi:motion-sensor'){svg.setAttribute('fill','currentColor');svg.setAttribute('stroke','none');}if(name==='fan'){const rotor=document.createElementNS(ns,'g');rotor.setAttribute('class','fan-rotor');for(const angle of [0,90,180,270]){const blade=document.createElementNS(ns,'path');blade.setAttribute('d',PanelIcons.fan);blade.setAttribute('transform','rotate('+angle+' 12 12)');rotor.append(blade);}const hub=document.createElementNS(ns,'circle');hub.setAttribute('class','fan-hub');hub.setAttribute('cx','12');hub.setAttribute('cy','12');hub.setAttribute('r','1.5');hub.setAttribute('fill','var(--icon-bg-off)');svg.append(rotor,hub);return svg;}const path=document.createElementNS(ns,'path');path.setAttribute('d',PanelIcons[name]||PanelIcons.toggle);svg.append(path);return svg;};
