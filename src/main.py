from getch import pause
import os
import requests
import signal
import sys

from context import Context
from settings import loadSettings, getSettingsMap

mark_for_termination = False
current = None


def signal_handler(signal, frame):
    print()
    print('download will stop.')

    global mark_for_termination
    mark_for_termination = True

    if current is not None:
        current.terminate()


signal.signal(signal.SIGINT, signal_handler)

load_success = loadSettings('settings.json')

if not load_success:
    try:
        input('press ENTER to close')
    except:
        pass

    sys.exit(0)

settings = getSettingsMap()

if not os.path.exists('downloads'):
    os.mkdir('downloads')

# Get a XSRF-TOKEN by sending a get request. The XSRF-TOKEN is in the response cookie.
s = requests.Session()
s.get('https://login.dlsite.com/login')

# Send a authentication request with the XSRF-TOKEN. NOTE: We have to follow the redirect.
res = s.post('https://login.dlsite.com/login', data={
    'login_id': settings['username'],
    'password': settings['password'],
    '_token': s.cookies['XSRF-TOKEN']
}, allow_redirects=True)

# Get the product count. The first call is needed to fill the proper cookies.
s.get('https://play.dlsite.com/api/product_count')
res = s.get('https://play.dlsite.com/api/product_count').json()

count = res['user']
page_limit = res['page_limit']

print('You have %d products.' % count)

page = 1
index = 0
works = []

# Fetch all purchased products.
while index < count:
    res = s.get(
        'https://play.dlsite.com/api/purchases?page={}'.format(page)).json()

    works.extend(
        map(lambda x: {'id': x['workno'], 'title': x['name']['ja_JP'], 'group': x['maker']['name']['ja_JP'], 'type': x['work_type'], 'date': x['sales_date']}, res['works']))

    page += 1
    index += page_limit

# Sort the works by purchase date.
works = sorted(works, key=lambda x: x['date'], reverse=True)

print('downloading products.')

for work in works:
    if mark_for_termination:
        break

    print()
    print('group: %s' % work['group'])
    print('title: %s' % work['title'])

    context = Context(s, work)
    current = context

    if not context.mkdir():
        if not mark_for_termination:
            print('already exists. skipping.')
        continue

    if not context.fetch_product_info():
        context.remove()
        continue

    if not context.download_image():
        context.remove()
        continue

    if not context.download_files():
        context.remove()
        continue

print()

if mark_for_termination:
    print('terminated.')
else:
    print('all products have been downloaded.')

pause('press any key to exit.')
