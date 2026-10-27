import unittest
import server
from pathlib import Path
class ViewerPINTest(unittest.TestCase):
 def test_browser_form_length_matches_role(self):
  root=Path(__file__).resolve().parents[1]/'www'
  self.assertIn('minlength="6"',(root/'login.html').read_text())
  self.assertIn('input.minLength=viewer?6:16',(root/'login.js').read_text())
 def test_numeric_six_digit_viewer_and_strong_editor(self):
  p={'viewer':'482619','editor':'editor-test-password'};self.assertEqual(server.validate_passwords(p),p)
 def test_weak_editor_and_non_pin_viewer_rejected(self):
  for p in [{'viewer':'482619','editor':'123456'},{'viewer':'abc123','editor':'editor-test-password'},{'viewer':'123','editor':'editor-test-password'}]:
   with self.assertRaises(ValueError):server.validate_passwords(p)
 def test_eight_digit_viewer_preserves_leading_zero(self):
  p={'viewer':'01234567','editor':'editor-test-password'}
  self.assertEqual(server.validate_passwords(p)['viewer'],'01234567')
  for value in ['12345','012345678','１２３４５６７８']:
   with self.assertRaises(ValueError):server.validate_passwords({'viewer':value,'editor':p['editor']})
 def test_old_long_passwords_and_unconfigured_mode(self):
  p={'viewer':'viewer-test-password','editor':'editor-test-password'};self.assertEqual(server.validate_passwords(p),p);self.assertEqual(server.validate_passwords({'viewer':'','editor':''}),{})
