import urllib.request
import urllib.error

try:
    response = urllib.request.urlopen('http://localhost:4008/api/laws/?page=1&page_size=9')
    print(response.read().decode())
except urllib.error.HTTPError as e:
    print(f'Status: {e.code}')
    print(e.read().decode())
