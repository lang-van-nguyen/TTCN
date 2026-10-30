import re, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

with open('diagnose_page.html', encoding='utf-8') as f:
    html = f.read()

api_urls = re.findall(r'"/api/([^"?#]{5,60})"', html)
api_urls = sorted(set(api_urls))
print('=== API endpoints tim thay ===')
for u in api_urls[:40]:
    print('/api/' + u)

ids = re.findall(r'"(shopid|itemid)"\s*:\s*(\d+)', html)
print('\n=== shopid / itemid ===')
for k, v in ids[:10]:
    print(f'  {k}: {v}')

# Tim them token/session
tokens = re.findall(r'"(csrftoken|SPC_F|SPC_SI|_gid)[^"]*"\s*:\s*"([^"]{5,60})"', html)
print('\n=== session tokens ===')
for k, v in tokens[:5]:
    print(f'  {k}: {v[:30]}...')
