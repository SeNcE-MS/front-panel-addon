import subprocess
import unittest
from pathlib import Path

class SensorDisplayTest(unittest.TestCase):
 def test_rounding_and_error_states_in_actual_renderer(self):
  app=(Path(__file__).resolve().parents[1]/'www'/'app.js').read_text().split('function canControl(')[0]
  checks="""
const assert=require('node:assert/strict');
const entity=state=>({entity_id:'sensor.test',state});
assert.equal(sensorState('temperature',entity('23.456')),'23.5');
assert.equal(sensorState('temperature',entity('23')),'23.0');
assert.equal(sensorState('temperature',entity('-0.04')),'0.0');
assert.equal(sensorState('temperature',entity('-4.26')),'-4.3');
assert.equal(sensorState('humidity',entity('56.78')),'57');
assert.equal(sensorState('humidity',entity('56.2')),'56');
assert.equal(sensorState('humidity',entity('0')),'0');
assert.equal(sensorState('temperature',entity('unavailable')),'사용 불가');
assert.equal(sensorState('humidity',entity('unknown')),'알 수 없음');
assert.equal(sensorState('temperature',undefined),'읽는 중…');
assert.equal(sensorState('window',entity('12.34')),'12.34');
const original=entity('23.456');sensorState('temperature',original);assert.equal(original.state,'23.456');
haError=true;assert.equal(sensorState('temperature',entity('23.456')),'연결 끊김');
"""
  result=subprocess.run(['node','-e',app+checks],capture_output=True,text=True)
  self.assertEqual(result.returncode,0,result.stderr)
