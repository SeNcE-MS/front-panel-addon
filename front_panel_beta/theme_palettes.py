"""Six independent accent families, each with designed light and dark surfaces.
Inspired by Radix semantic scales and Adaptive Mushroom's surface hierarchy.
See theme-design-notes.md for sources and rationale. No network dependency.
"""
PALETTES={
 'navy':('블루',{'light':['#f5f7fb','#ffffff','#17243b','#5b687b','#245dcc','#e6efff','#dce2ec'],'dark':['#10141d','#1a2230','#edf2fc','#a1afc4','#9bbdff','#243550','#303c50']}),
 'ocean':('민트',{'light':['#f3f8f7','#ffffff','#173b38','#566e6a','#14776f','#dff4ee','#d3e3df'],'dark':['#0f1918','#1a2825','#e8f6f1','#a0b9b0','#7ad5bc','#204339','#32473e']}),
 'forest':('포레스트',{'light':['#f5f8f2','#ffffff','#293d25','#606f58','#477333','#e5f0dc','#d9e3d1'],'dark':['#151a12','#232c1f','#eef5e7','#adbba3','#b1d88b','#35452a','#3c4734']}),
 'plum':('라벤더',{'light':['#f8f5fb','#ffffff','#382d4b','#70637e','#7851a8','#efe5fb','#e2d9ec'],'dark':['#19151f','#292131','#f2ecfa','#bcaecb','#c8a6ec','#443254','#493a56']}),
 'ember':('선셋',{'light':['#fcf7f1','#ffffff','#49331e','#806448','#a55b1b','#f9e9d4','#e6d8c6'],'dark':['#1b1713','#2b231c','#f8efe5','#c5b39e','#e8b77b','#4c3824','#4b3b2c']}),
 'slate':('모노',{'light':['#f5f6f7','#ffffff','#252b33','#626b77','#4c5c70','#e5e9ef','#d8dde4'],'dark':['#15171a','#24272c','#eef0f3','#adb4bf','#c1c9d5','#353e4b','#424953']}),
 'glass':('글라스',{'light':['#dcdedc','#d1d3d1','#292b2d','#555956','#363a38','#ffffff','#a4aaa5'],'dark':['#1b1d23','#303237','#f5f5f4','#c0c2c2','#f2f3f2','#ffffff','#66696e']})}
TOKEN_COLORS=('line','onActive','onAccent','switchOn','switchOff','thumb','soft','iconBgOff','iconBgOn','iconOff','iconOn','activeBorder','hover')
def blend(a,b,weight):
 values=[round(int(a[i:i+2],16)*(1-weight)+int(b[i:i+2],16)*weight) for i in (1,3,5)]
 return '#'+''.join(f'{value:02x}' for value in values)
def preset(key,mode='dark'):
 if mode not in ['light','dark']:raise ValueError('화면 모드 오류')
 colors=dict(zip(('background','surface','text','muted','accent','active','line'),PALETTES[key][1][mode]))
 on_accent='#ffffff' if mode=='light' else colors['background']
 colors.update(mode=mode,onActive=colors['text'],onAccent=on_accent,switchOn=colors['accent'],switchOff=colors['line'],thumb=on_accent,soft=colors['active'],iconBgOff=colors['background'],iconBgOn=colors['accent'],iconOff=colors['muted'],iconOn=on_accent,activeBorder=blend(colors['active'],colors['accent'],.3),hover=blend(colors['surface'],colors['line'],.35))
 if key=='glass':
  colors.update(onActive='#242629',switchOn='#288955',thumb='#ffffff',soft='#c9ceca' if mode=='light' else '#47494e',iconBgOff=colors['surface'],iconBgOn='#e8e9e7',iconOn='#343638',activeBorder='#ffffff')
 return colors
