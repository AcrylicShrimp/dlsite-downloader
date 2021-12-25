import os
import re
import requests
import shutil
import subprocess
import sys
from tqdm import tqdm

from settings import loadSettings, getSettingsMap

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
    print()
    print('group: %s' % work['group'])
    print('title: %s' % work['title'])
    error_count = 0

    # Replace invalid path characters with '_'.
    group = re.sub(r'[\\/:*?"<>|]', '_', work['group'])
    title = re.sub(r'[\\/:*?"<>|]', '_', work['title'])

    # Create a directory for the work.
    if not os.path.exists('downloads/{}'.format(group)):
        os.mkdir('downloads/{}'.format(group))

    if not os.path.exists('downloads/{}/{}'.format(group, title)):
        os.mkdir(
            'downloads/{}/{}'.format(group, title))
    else:
        print('already exists. skipping.')
        continue

    def download_file(file_url, file_size, file_name):
        with s.get(file_url, stream=True, allow_redirects=True) as r:
            r.raise_for_status()

            with tqdm.wrapattr(open('downloads/{}/{}/{}'.format(group, title, file_name), 'wb'), 'write', file_size, desc=file_name) as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

    # Error loop.
    while True:
        try:
            # Fetch product info.
            print('fetching product info...', end=' ')

            res = s.get(
                'https://www.dlsite.com/maniax/api/=/product.json?workno={}'.format(work['id'])).json()[0]

            print('Ok')

            # Image
            image_url = 'https:{}'.format(res['image_main']['url'])
            image_size = int(res['image_main']['file_size'])
            image_name = res['image_main']['file_name']
            download_file(image_url, image_size, image_name)

            # Files
            if len(res['contents']) == 1:
                # Single file.
                file_url = 'https://www.dlsite.com/maniax/download/=/product_id/{}.html'.format(
                    work['id'])
                file_size = int(res['contents'][0]['file_size'])
                file_name = res['contents'][0]['file_name']
                download_file(file_url, file_size, file_name)
            else:
                # Multiple files.
                for index, file in enumerate(res['contents']):
                    file_url = 'https://www.dlsite.com/maniax/download/=/number/{}/product_id/{}.html'.format(
                        index + 1, work['id'])
                    file_size = int(file['file_size'])
                    file_name = file['file_name']
                    download_file(file_url, file_size, file_name)

                # Run the self extracting archive if the extension is .exe.
                if res['contents'][0]['file_name'].endswith('.exe'):
                    print('extracting files...', end=' ')

                    subprocess.run([
                        'downloads/{}/{}/{}'.format(group, title,
                                                    res['contents'][0]['file_name']),
                        '-s2', '-d__tmp'], cwd='downloads/{}/{}'.format(group, title))

                    # Remove the container files.
                    for file in res['contents']:
                        os.remove('downloads/{}/{}/{}'.format(group,
                                  title, file['file_name']))

                    # Find the directory name of the extracted files.
                    dirs = os.listdir(
                        'downloads/{}/{}/__tmp'.format(group, title))

                    if len(dirs) == 1:
                        # The SFX contains root directory.
                    src = 'downloads/{}/{}/__tmp/{}'.format(
                            group, title, dirs[0])
                    else:
                        # The SFX not have root directory.
                        src = 'downloads/{}/{}/__tmp'.format(
                            group, title)

                    dst = 'downloads/{}/{}'.format(group, title)

                    # Move the extracted files to the current.
                    for file in os.listdir(src):
                        shutil.move('{}/{}'.format(src, file),
                                    dst)

                    # Remove the extracted directory.
                    shutil.rmtree('downloads/{}/{}/__tmp'.format(group, title))

                    print('Ok')

            break

        except Exception as err:
            error_count += 1
            print('an error occured: %s' % err)

            if error_count == 3:
                print('download failed.')
                break
            else:
                print('[count=%d] retrying.' % error_count)

print()
print('all products have been downloaded.')
