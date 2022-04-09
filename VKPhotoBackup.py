import requests
from time import sleep
import json
from tqdm import tqdm


class VKPhotoBackup:
    def __init__(self, owner_id, vk_access_token, ya_disc_token):
        self.owner_id = owner_id
        self.vk_access_token = vk_access_token
        self.ya_disc_token = ya_disc_token

    def get_photos_list_from_vk(self, albums, photos_count):
        url = 'https://api.vk.com/method/photos.get'
        params = {
            'access_token': self.vk_access_token,
            'v': '5.131',
            'owner_id': self.owner_id,
            'count': photos_count,
            'extended': '1',
            'rev': '1'
        }
        photos_list = []
        print('Getting photos from VK...')
        for album in albums:
            params['album_id'] = album
            resp = requests.get(url, params=params)
            if resp.status_code == 200:
                if 'response' in resp.json().keys():
                    if len(photos_list) < photos_count:
                        for photo in resp.json()['response']['items']:
                            photos_list.append(photo)
                            if len(photos_list) == photos_count:
                                break
                elif 'error' in resp.json().keys():
                    print(f"In album {album}: {resp.json()['error']['error_msg']}")
                else:
                    print(f"Unknown error in album {album}")
            else:
                print(f"Response status code: {resp.status_code} instead of 200 in album {album}")
        print(f'{len(photos_list)} photos received.')
        return photos_list

    def prepare_photos_upload(self, photos_list):
        photos_upload_list = []
        for photo in tqdm(photos_list, bar_format='{l_bar}{bar}', desc='Processing photos'):
            date = photo['date']
            likes = photo['likes']['count']
            height = 0
            width = 0
            max_size = 0
            max_size_url = ''
            for size in photo['sizes']:
                curr_size = int(size['height']) * int(size['width'])
                if curr_size > max_size:
                    max_size = curr_size
                    max_size_url = size['url']
                    height = size['height']
                    width = size['width']
            photo_upload = {'filename': f'{str(likes)}.jpg',
                            'height': str(height),
                            'width': str(width),
                            'url': max_size_url,
                            'date': str(date)
                            }
            photos_upload_list.append(photo_upload)
            sleep(0.25)
        return photos_upload_list

    def upload_photos(self, photos_upload_list):
        print('Preparing to upload photos.')
        log_filename = 'log_upload.json'
        log_data = []
        upload_url = 'https://cloud-api.yandex.net/v1/disk/resources/upload'
        resource_url = 'https://cloud-api.yandex.net/v1/disk/resources'
        headers = {'Content-Type': 'application/json', 'Authorization': f'OAuth {self.ya_disc_token}'}
        params = {'path': 'disk:/', 'fields': '_embedded.items.name'}
        resp = requests.get(resource_url, headers=headers, params=params)
        upload_folder = {'name': 'VK_PhotoBackup'}
        if upload_folder not in resp.json()['_embedded']['items']:
            params = {'path': 'VK_PhotoBackup'}
            resp = requests.put(resource_url, headers=headers, params=params)
            if resp.status_code != 201:
                error_msg = 'Error: can not create upload folder'
                return error_msg
        for photo in tqdm(photos_upload_list, bar_format='{l_bar}{bar}', desc='Uploading photos on the YandexDisc'):
            params = {'path': f'VK_PhotoBackup/{photo["filename"]}', 'fields': 'name'}
            resp_chekname = requests.get(resource_url, headers=headers, params=params)
            if 'name' in resp_chekname.json().keys():
                photo['filename'] = photo['filename'].split('.jpg')[0] + '_' + photo['date'] + '.jpg'
            params = {'path': f'VK_PhotoBackup/{photo["filename"]}', 'url': photo['url']}
            resp_upload = requests.post(upload_url, headers=headers, params=params)
            for try_status in range(5):
                resp_status = requests.get(resp_upload.json()['href'], headers=headers)
                if resp_status.json()['status'] == 'success':
                    break
                elif resp_status.json()['status'] == 'in-progress':
                    sleep(2)
                else:
                    error_msg = f'Upload operation id = {resp_upload.json()["href"]} falled.'
                    return error_msg
            resp_status = requests.get(resp_upload.json()['href'], headers=headers)
            if resp_status.json()['status'] != 'success':
                error_msg = f'Upload operation id = {resp_upload.json()["href"]} timeout exceed.'
                return error_msg
            log_info = {'file_name': photo['filename'], 'height': photo['height'], 'width': photo['width']}
            log_data.append(log_info)
        with open(log_filename, 'w') as log_file:
            json.dump(log_data, log_file)
        return 'Photos uploaded successfully'

    def backup_photos(self, albums=('wall', 'profile'), photos_count=5):
        photos_list = self.get_photos_list_from_vk(albums, photos_count)
        photos_upload_list = self.prepare_photos_upload(photos_list)
        result_upload = self.upload_photos(photos_upload_list)
        print(result_upload)
