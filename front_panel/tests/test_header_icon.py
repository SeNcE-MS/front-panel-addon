import copy,unittest
from unittest.mock import patch
from panel_config import DEFAULT,validate
class HeaderIconSettingsTest(unittest.TestCase):
 def test_legacy_and_preservation(self):
  raw=validate(copy.deepcopy(DEFAULT));raw['display'].pop('header_icon',None);before=copy.deepcopy(raw);saved=validate(raw);self.assertEqual(saved['display'].pop('header_icon',None),'');self.assertEqual(saved,before)
 def test_paths(self):
  for value in ['', 'front-panel/icon.png','my-icon.webp','아이콘.png']:
   raw=copy.deepcopy(DEFAULT);raw['display']['header_icon']=value;self.assertEqual(validate(raw)['display']['header_icon'],value)
 def test_reject_unsafe(self):
  for value in ['../secrets.yaml','/local/icon.png','https://example.com/x.png','x.svg','a/../../x.png','a%2fx.png','x.png?q=1',True,None]:
   raw=copy.deepcopy(DEFAULT);raw['display']['header_icon']=value
   with self.assertRaises(ValueError):validate(raw)
 def test_header_disabled_preserves_path(self):
  raw=copy.deepcopy(DEFAULT);raw['display'].update(header=False,header_icon='front-panel/icon.png');self.assertEqual(validate(raw)['display']['header_icon'],'front-panel/icon.png')

class HeaderIconReaderTest(unittest.TestCase):
 def test_fixed_origin_no_token_and_png_only(self):
  from header_icon import read_icon
  from unittest.mock import MagicMock
  response=MagicMock();response.__enter__.return_value.read.return_value=b'\x89PNG\r\n\x1a\nfixture'
  with patch('header_icon.build_opener') as factory:
   factory.return_value.open.return_value=response
   data,mime=read_icon('front-panel/icon.png')
   request=factory.return_value.open.call_args.args[0]
   self.assertEqual(request.full_url,'http://homeassistant.local:8123/local/front-panel/icon.png')
   self.assertNotIn('Authorization',request.headers)
   self.assertEqual(mime,'image/png')
 def test_unsafe_path_never_fetches(self):
  from header_icon import read_icon
  with patch('header_icon.build_opener') as factory:
   with self.assertRaises(ValueError):read_icon('../secrets.yaml')
   factory.assert_not_called()
 def test_size_and_nonimage_rejected(self):
  from header_icon import read_icon,MAX_SIZE
  from unittest.mock import MagicMock
  for data in [b'<html>not an image</html>',b'x'*(MAX_SIZE+1)]:
   response=MagicMock();response.__enter__.return_value.read.return_value=data
   with patch('header_icon.build_opener') as factory:
    factory.return_value.open.return_value=response
    with self.assertRaises(ValueError):read_icon('fake.png')
 def test_redirect_blocked(self):
  from header_icon import NoRedirect
  self.assertIsNone(NoRedirect().redirect_request(None,None,302,'',{},'https://example.com/x.png'))
