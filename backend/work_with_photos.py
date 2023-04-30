import yadisk
import re
import requests
import os

class DownloadPhotos:

    @staticmethod
    def login_to_cloud(access_token):
        y = yadisk.YaDisk(token=access_token)
        return y

    @staticmethod
    def make_files_folder(agent):
        if not agent.exists('files'):
            agent.mkdir('files')

    @staticmethod
    def get_url_to_files(agent):
        return agent.get_public_url('/files')

    @staticmethod
    def upload_to_cloud(agent, groupname, photo_url):

        pattern = max(re.search(r'uniq_tag=(-?\w+)-?(\w+)?-?(\w+)?&?', photo_url).groups(),
                      key=lambda x: len(x) if x else 0)[:10]
        if not agent.exists('files'):
            agent.mkdir('files')
        if not agent.exists(f'/files/{groupname}'):
            agent.mkdir(f'/files/{groupname}')
        if not agent.exists(f"files/{groupname}/{pattern}.jpg"):
            agent.upload_url(photo_url, f"files/{groupname}/{pattern}.jpg")

    @staticmethod
    def to_local(groupname, photo_url):
        """Скачивает фотографии поста на локальную машину в директорию workdir/files/groupname"""
        response = requests.get(photo_url)
        pattern = max(re.search(r'uniq_tag=(-?\w+)-?(\w+)?-?(\w+)?&?', response.url).groups(),
                      key=lambda x: len(x) if x else 0)[:10]
        workdir = os.getcwd()
        if not os.path.exists(f'{workdir}/files/{groupname}'):
            os.makedirs(f'{workdir}/files/{groupname}')
        if not os.path.exists(f'{workdir}/files/{groupname}/{pattern}.jpg'):
            with open(f'{workdir}/files/{groupname}/{pattern}.jpg', 'wb') as file:
                file.write(response.content)


"""if attachment_type == 'photo':
    self.download_and_upload_photo(access_token='y0_AgAAAAAICbaeAAnQoQAAAADhyumQnrDWPKq4RJaNvozS0MynI_nnHew',
                               groupname=groupname,
                               photo_url=attachment)"""
