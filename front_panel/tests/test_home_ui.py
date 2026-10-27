import subprocess,unittest
from pathlib import Path
class HomeUITest(unittest.TestCase):
 def test_idle_return_and_appliance_remaining_helpers(self):
  file=Path(__file__).resolve().parents[1]/'www/home.js'
  script=r"""
const assert=require('node:assert/strict');const h=require(process.argv[1]);
const cfg={enabled:true,auto_return:true};
assert.equal(h.shouldReturn(cfg,'room-1',0,299999,false),false);
assert.equal(h.shouldReturn(cfg,'room-1',0,300000,false),true);
assert.equal(h.shouldReturn(cfg,'room-1',250000,300000,false),false);
assert.equal(h.shouldReturn({...cfg,enabled:false},'room-1',0,900000,false),false);
assert.equal(h.shouldReturn({...cfg,auto_return:false},'room-1',0,900000,false),false);
assert.equal(h.shouldReturn(cfg,h.HOME_ID,0,900000,false),false);
assert.equal(h.shouldReturn(cfg,'room-1',0,900000,true),false);
assert.equal(h.remaining({state:'65',unit:'min'},0),'1시간 05분');
assert.equal(h.remaining({state:'120',unit:'s'},0),'2분');
assert.equal(h.remaining({state:'2026-10-24T07:00:00Z',attributes:{device_class:'timestamp'}},Date.parse('2026-10-24T06:40:00Z')),'20분');
assert.equal(h.remaining({state:'unknown'},0),'시간 확인 중');
assert.equal(h.remaining({state:'2026-10-24T07:00:00Z'},Date.parse('2026-10-24T08:00:00Z')),'마무리 중');
assert.equal(h.isActive({enabled:true,state_entity:'sensor.w',active_states:['running']},{'sensor.w':{state:'running'}},false),true);
assert.equal(h.isActive({enabled:true,state_entity:'sensor.w',active_states:['running']},{'sensor.w':{state:'power_off'}},false),false);
assert.equal(h.isActive({enabled:true,state_entity:'sensor.w',active_states:['running']},{'sensor.w':{state:'running'}},true),false);
"""
  result=subprocess.run(['node','-e',script,str(file)],capture_output=True,text=True)
  self.assertEqual(result.returncode,0,result.stderr)
