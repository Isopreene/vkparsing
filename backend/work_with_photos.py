import yadisk
import re
import pymysql

class PhotosToCloud:

    @staticmethod
    def download_and_upload_photo(access_token, groupname, photo_url):
        y = yadisk.YaDisk(token=access_token)
        pattern = max(re.search(r'uniq_tag=(-?\w+)-?(\w+)?-?(\w+)?&?', photo_url).groups(),
                      key=lambda x: len(x) if x else 0)[:10]
        path_to_file = f"{groupname}/{pattern}.jpg"
        if not y.exists(groupname):
            y.mkdir(groupname)
        if not y.exists(path_to_file):
            y.upload_url(photo_url, path_to_file)


"""if attachment_type == 'photo':
    self.download_and_upload_photo(access_token='y0_AgAAAAAICbaeAAnQoQAAAADhyumQnrDWPKq4RJaNvozS0MynI_nnHew',
                               groupname=groupname,
                               photo_url=attachment)"""


#path_to_group = parser.create_group(directory, group)
