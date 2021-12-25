import os
import re
import shutil
import subprocess
from tqdm import tqdm

from retry_on_failure import retry_on_failure


class Context:
    def __init__(self, s, work):
        self.s = s
        self.work = work
        self.base_dir = None
        self.res = None
        self.mark_for_termination = False

    def terminate(self):
        self.mark_for_termination = True

    def mkdir(self):
        if self.mark_for_termination:
            return False

        print('making directory...', end=' ')

        # Replace invalid path characters with '_'.
        group = re.sub(r'[\\/:*?"<>|]', '_', self.work['group'])
        title = re.sub(r'[\\/:*?"<>|]', '_', self.work['title'])

        if not os.path.exists(os.path.join('downloads', self.work['type'])):
            os.mkdir(os.path.join('downloads', self.work['type']))

        if not os.path.exists(os.path.join('downloads', self.work['type'], group)):
            os.mkdir(os.path.join('downloads', self.work['type'], group))

        if not os.path.exists(os.path.join('downloads', self.work['type'], group, title)):
            os.mkdir(os.path.join(
                'downloads', self.work['type'], group, title))
        else:
            return False

        self.base_dir = os.path.join(
            'downloads', self.work['type'], group, title)

        print('Ok')

        return True

    @retry_on_failure
    def fetch_product_info(self):
        if self.mark_for_termination:
            return False

        print('fetching product info...', end=' ')

        self.res = self.s.get(
            'https://www.dlsite.com/maniax/api/=/product.json?workno={}'.format(self.work['id'])).json()[0]

        print('Ok')

        return True

    def download_image(self):
        image_url = 'https:{}'.format(self.res['image_main']['url'])
        image_size = int(self.res['image_main']['file_size'])
        image_name = self.res['image_main']['file_name']
        return self.__download_file(image_url, image_size, image_name)

    def download_files(self):
        if len(self.res['contents']) == 1:
            # Single file.
            file_url = 'https://www.dlsite.com/maniax/download/=/product_id/{}.html'.format(
                self.work['id'])
            file_size = int(self.res['contents'][0]['file_size'])
            file_name = self.res['contents'][0]['file_name']
            return self.__download_file(file_url, file_size, file_name)

        # Multiple files.
        for index, file in enumerate(self.res['contents']):
            file_url = 'https://www.dlsite.com/maniax/download/=/number/{}/product_id/{}.html'.format(
                index + 1, self.work['id'])
            file_size = int(file['file_size'])
            file_name = file['file_name']

            if not self.__download_file(file_url, file_size, file_name):
                return False

        # Run the self extracting archive if the extension is .exe.
        if self.res['contents'][0]['file_name'].endswith('.exe'):
            if not self.extract_sfx():
                return False

        return True

    @retry_on_failure
    def extract_sfx(self):
        if self.mark_for_termination:
            return False

        print('extracting files...', end=' ')

        subprocess.run([
            '{}/{}'.format(self.base_dir,
                           self.res['contents'][0]['file_name']),
            '-s2',
            '-d__tmp'
        ], cwd=self.base_dir)

        # Remove the container files.
        for file in self.res['contents']:
            os.remove('{}/{}'.format(self.base_dir, file['file_name']))

        # Find the directory name of the extracted files.
        dirs = os.listdir('{}/__tmp'.format(self.base_dir))

        if len(dirs) == 1:
            # The SFX contains root directory.
            src = '{}/__tmp/{}'.format(self.base_dir, dirs[0])
        else:
            # The SFX not have root directory.
            src = '{}/__tmp'.format(self.base_dir)

        dst = '{}'.format(self.base_dir)

        # Move the extracted files to the current.
        for file in os.listdir(src):
            shutil.move('{}/{}'.format(src, file), dst)

        # Remove the extracted directory.
        shutil.rmtree('{}/__tmp'.format(self.base_dir))

        print('Ok')

        return True

    def remove(self):
        print('removing...', end=' ')

        shutil.rmtree(self.base_dir)

        print('Ok')

    @retry_on_failure
    def __download_file(self, file_url, file_size, file_name):
        if self.mark_for_termination:
            return False

        with self.s.get(file_url, stream=True, allow_redirects=True) as r:
            r.raise_for_status()

            with tqdm.wrapattr(open(os.path.join(self.base_dir, file_name), 'wb'), 'write', file_size, desc=file_name) as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if self.mark_for_termination:
                        return False

                    f.write(chunk)

        return True
