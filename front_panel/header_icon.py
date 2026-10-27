"""Read only a configured raster image from HA's public www (/local) directory."""
import re
from urllib.parse import quote
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.error import URLError,HTTPError
PATH=re.compile(r'(?:[A-Za-z0-9가-힣_-]+/)*[A-Za-z0-9가-힣_ .-]+\.(?:png|jpe?g|webp|gif)',re.I)
MAX_SIZE=2*1024*1024

def validate_icon_path(value):
 if not isinstance(value,str) or len(value)>240 or value and not PATH.fullmatch(value):raise ValueError('www 폴더 안의 이미지 상대 경로를 입력하세요')
 return value

class NoRedirect(HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):return None

def read_icon(path):
 validate_icon_path(path)
 if not path:raise ValueError('아이콘 미설정')
 # Fixed HA origin only. No tokens, arbitrary hosts, filesystem access, or redirects.
 req=Request('http://homeassistant.local:8123/local/'+quote(path,safe='/'),headers={'Accept':'image/png,image/jpeg,image/webp,image/gif'},method='GET')
 try:
  with build_opener(NoRedirect).open(req,timeout=5) as response:data=response.read(MAX_SIZE+1)
 except (URLError,HTTPError,TimeoutError,OSError):raise ValueError('www 이미지 파일을 읽을 수 없습니다') from None
 if len(data)>MAX_SIZE:raise ValueError('이미지는 2MB 이하로 준비하세요')
 if data.startswith(b'\x89PNG\r\n\x1a\n'):mime='image/png'
 elif data.startswith(b'\xff\xd8\xff'):mime='image/jpeg'
 elif data.startswith((b'GIF87a',b'GIF89a')):mime='image/gif'
 elif data.startswith(b'RIFF') and data[8:12]==b'WEBP':mime='image/webp'
 else:raise ValueError('PNG, JPG, WEBP, GIF 이미지만 지원합니다')
 return data,mime
