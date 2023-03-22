import vk_api
import requests
from datetime import datetime
import os
import re
import pymysql
import json
import vk_captchasolver as vc


class MainMethods:
    """Основные методы для работы в программе"""

    @staticmethod
    def get_param_from_url(url, param_name):
        print(url)
        return [i.split("=")[-1] for i in url.split("?", 1)[-1].split("&") if i.startswith(param_name + "=")][0]

    def captcha_handler(self, captcha):
        sid = self.get_param_from_url(captcha.get_url(), "sid")  # Парсим параметр sid из ссылки
        s = self.get_param_from_url(captcha.get_url(), "s")  # Парсим параметр s из ссылки
        return captcha.try_again(
            vc.solve(sid=int(sid), s=int(s)))  # Просим вк попробовать еще раз вместе с решенной каптчей

    def vk_login(self, group_input) -> dict | None:
        """логинится в vk, заходит в группу name и получает все посты"""
        # must enter login and password through input, make it later
        login = '+79963546774'
        password = 'Kozzgsf0896'
        token = 'vk1.a.DgiSODXfBYBhQf8wRMVEvzDLhSJjLnZlf_TJFfxI7oE9bzPsYNsYvy4tdIPc8ZchPOqNSAzzrzWv6rpBhnvSlXo_lDi2jf8M_A3ayCJNfzIQwGovZEPzYRlJjd4RkiOt1ZiATWo2DMrZBplTW4id1zjpNDt4-0JHLCX-fa-VzINsLOv7efCop_YMzGnN61G0GB2M2KmELgcfN-DwCD9vyw'
        vk_session = vk_api.VkApi(login=login,
                                  password=password,
                                  token=token,
                                  captcha_handler=self.captcha_handler)
        vk_session.auth()
        vk = vk_session.get_api()
        id_ = re.search(r'vk.com/id(\d+)', group_input)
        short_name = re.search(r'vk.com/(\w+)', group_input)
        if id_:
            posts = vk.wall.get(owner_id=-int(id_.group(1)), count=30,
                                filter='all')  # dict, получаем все посты, count * 25 = их количество
        elif short_name:
            posts = vk.wall.get(domain=short_name.group(1), count=30,
                                filter='all')  # dict, получаем все посты, count * 25 = их количество
        else:
            print(f'Неверно введён адрес или id сообщества')
            return
        return posts

    @staticmethod
    def create_group(directory, groupname):
        try:
            if not os.path.exists(f'{directory}/files'):
                os.mkdir(f'{directory}/files')
            if not os.path.exists(f'{directory}/files/{groupname}'):
                os.mkdir(f'{directory}/files/{groupname}')
            directory = f'{directory}/files/{groupname}'
        except Exception as e:
            print(e, 'Не удалось создать родительские папки')
        return directory

    @staticmethod
    def create_json(groupname, data):
        with open(f'{groupname}.json', 'w') as file:
            for row in data:
                json.dump(row, file, indent=4, default=str, ensure_ascii=False)
                file.write('\n')


class Post:
    """каждый пост с атрибутами вложений (текста, картинок, видео, документов и т.д.)"""

    def __init__(self):
        self.__text = None
        self.__date = None
        self.__id_ = None
        self.__attachments = {'audio': [], 'video': [], 'doc': [], 'link': [], 'poll': [], 'photo': []}
        self.__is_repost = False
        self.__hash = None

    @property
    def text(self):
        return self.__text

    @text.setter
    def text(self, obj):
        self.__text = obj

    @property
    def date(self):
        return self.__date

    @date.setter
    def date(self, obj):
        self.__date = obj

    @property
    def id_(self):
        return self.__id_

    @id_.setter
    def id_(self, obj):
        self.__id_ = obj

    @property
    def attachments(self):
        return self.__attachments

    def add_attachment(self, type_, obj):
        self.__attachments[type_].append(obj)

    @property
    def hash(self):
        return self.__hash

    @hash.setter
    def hash(self, obj):
        if self.hash is None:
            self.__hash = obj
        else:
            raise AttributeError('Хэш уже задан')

    @property
    def is_repost(self):
        return self.__is_repost

    @is_repost.setter
    def is_repost(self, obj):
        self.__is_repost = obj

    @staticmethod
    def get_poll(poll):
        poll_image = poll.get('photo')
        if poll_image:
            poll_image_url = max(poll_image['images'], key=lambda x: x['width'] * x['height'])['url']
        votes = []
        poll_answers_texts = []
        for answer in poll['answers']:
            poll_answers_texts.append(answer['text'])
            votes.append(answer['votes'])
        poll_answers = [poll['question'], {answer: vote for answer, vote in zip(poll_answers_texts, votes)}]
        return {'image': poll_image_url if poll_image else None, 'answers': poll_answers}


class PostsHandler:
    """обрабатывает dict всех постов, создаёт каждому посту объект класса Post и присваивает ему атрибуты для записи"""

    def __init__(self, data_from_parser):

        self.__data = data_from_parser
        self.__processed_posts = []  # список объектов класса Post, добавляем уже обработанные посты

    @property
    def data(self):
        return self.__data

    @property
    def processed_posts(self):
        return self.__processed_posts

    def add_processed_post(self, post):
        self.__processed_posts.append(post)

    @staticmethod
    def add_attachment(attachment, post_obj):
        match attachment.get('type'):
            case 'photo':
                photo = attachment['photo']
                link = max(photo['sizes'], key=lambda x: x['height'] * x['width'])['url']
                post_obj.add_attachment('photo', link)
            case 'video':
                video = attachment['video']
                link = f"https://vk.com/video{video['owner_id']}_{video['id']}"  # _{video['access_key']}
                post_obj.add_attachment('video', link)
                # post_obj.add_attachment('video', video)
            case 'link':
                link = attachment['link']
                post_obj.add_attachment('link', link['url'])
            case 'audio':
                audio = attachment['audio']
                post_obj.add_attachment('audio', audio['url'])
            case 'doc':  # документы – от 0 до n
                doc = attachment['doc']
                post_obj.add_attachment('doc', doc['url'])
            case 'poll':  # опрос – от 0 до 1
                poll = attachment['poll']
                post_obj.add_attachment('doc', post_obj.get_poll(poll))

    @staticmethod
    def download_photo(attachment, directory):
        match attachment.get('type'):
            case 'photo':
                photo = attachment['photo']
                link = max(photo['sizes'], key=lambda x: x['height'] * x['width'])['url']
                response = requests.get(link)
                pattern = max(re.search(r'uniq_tag=(-?\w+)-?(\w+)?-?(\w+)?&?', response.url).groups(), key=lambda x: len(x) if x else 0)[:10]
                filename = f"{pattern}.jpg"
                if not os.path.exists(f'{directory}/{filename}'):
                    with open(f'{directory}/{filename}', 'wb') as file:
                        file.write(response.content)

    def main(self, dir_to_group):
        for post in self.data['items']:  # проходимся по dict и получаем list

            new_post = Post()
            new_post.hash = post['hash']
            new_post.date = datetime.fromtimestamp(post['date']).strftime('%Y-%m-%d')

            if post.get('copy_history'):  # если репост
                new_post.is_repost = True
                post = post['copy_history'][0]

            new_post.text = post['text']
            new_post.id_ = post['owner_id']
            attachments = post['attachments']

            for attachment in attachments:
                self.add_attachment(attachment, new_post)
                self.download_photo(attachment, dir_to_group)

            self.add_processed_post(new_post)


class MySQLHandler:

    def __init__(self, data_from_post_handler):
        """Получает данные в виде списка объектов класса Post и заносит их в базу данных. Проверяет на хэши, если такой уже есть в БД, то не заносит"""
        self.__posts = data_from_post_handler

    @staticmethod
    def create_database(host, user, password):
        """создать базу данных, куда будем записывать всё"""
        try:
            with pymysql.connect(host=host, user=user, password=password) as connection:
                with connection.cursor() as cursor:
                    cursor.execute('show databases')
                    if ('vk',) not in cursor:
                        cursor.execute('create database vk')
        except Exception as e:
            raise e

    @staticmethod
    def create_table(host, user, password, database, groupname):
        """Работаем с базой данных vk"""
        try:
            with pymysql.connect(host=host, user=user, password=password, database=database) as connection:
                with connection.cursor() as cursor:
                    cursor.execute('show tables')
                    if (groupname,) not in cursor:
                        query = f'create table {groupname}(id INT PRIMARY KEY AUTO_INCREMENT, post_hash varchar(255), ' \
                                'post_text varchar(255), post_date date, post_id varchar(255), is_repost bool, attachment_1 varchar(255), ' \
                                'attachment_2 varchar(255), attachment_3 varchar(255), attachment_4 varchar(255), ' \
                                'attachment_5 varchar(255), attachment_6 varchar(255), attachment_7 varchar(255), ' \
                                'attachment_8 varchar(255), attachment_9 varchar(255), attachment_10 varchar(255))'  # создали таблицу с нужными данными
                        cursor.execute(query)
        except Exception as e:
            raise e

    def add_to_database(self, host, user, password, database, groupname):
        try:
            with pymysql.connect(host=host, user=user, password=password, database=database) as connection:
                with connection.cursor() as cursor:
                    for post in self.__posts:
                        check_hash = post.hash
                        query = f'select * from {groupname} where post_hash = %s'  # есть ли хэш в таблице
                        cursor.execute(query, (check_hash,))
                        if any((i for i in cursor)):
                            pass
                        else:
                            text = post.text[:252] + '...' if len(post.text) >= 252 else post.text
                            id_ = post.id_
                            date = post.date
                            is_repost = post.is_repost
                            attachments = post.attachments
                            query = f'insert into {groupname}(post_hash, post_text, post_date, post_id, is_repost) values (%s, %s, %s, %s, %s)'
                            cursor.execute(query, (check_hash, text, date, id_, is_repost))  # внесли текст поста, id создателя, дату поста и метку репоста (является/не является)
                            counter = 0
                            for attachment_type, attachment_list in [i for i in attachments.items() if i[1]]:
                                for attachment in attachment_list:
                                    counter += 1
                                    column_name = f'attachment_{counter}'
                                    attachment_name = f'{attachment_type}: {attachment}'
                                    query = f"update {groupname} set {column_name} = (%s) where post_hash = %s"
                                    cursor.execute(query, [attachment_name, check_hash])
                            connection.commit()

        except Exception as e:
            raise e

    @staticmethod
    def get_from_database(host, user, password, database, groupname):
        try:
            with pymysql.connect(host=host, user=user, password=password, database=database) as connection:
                with connection.cursor() as cursor:
                    query = f'select * from {groupname} where id <= 100'
                    cursor.execute(query)
                    data = cursor.fetchall()
                    query = f'SHOW COLUMNS FROM {groupname}'
                    cursor.execute(query)
                    columns = tuple(map(lambda x: x[0], cursor.fetchall()))
                    return ({key: value for key, value in zip(columns, row) if value} for row in data)
        except Exception as e:
            raise e


if __name__ == '__main__':

    group_input = 'https://vk.com/slabzveno'
    groupname = group_input.split("/")[-1] # в инпут #https://vk.com/slabzveno  https://vk.com/respublicana
    directory = '/Users/mirnauki/Downloads'  # в инпут?
    parser = MainMethods()
    collected_data = parser.vk_login(group_input)
    path_to_group = parser.create_group(directory, groupname)
    data_processing = PostsHandler(collected_data)
    data_processing.main(path_to_group)
    posts = data_processing.processed_posts
    vk_sql = MySQLHandler(posts)
    arguments = {'host': 'localhost', 'user': 'root', 'password': '12august'}  # добавить инпуты вместо логина и пароля
    vk_sql.create_database(**arguments)
    vk_sql.create_table(**arguments, database='vk', groupname=groupname)
    vk_sql.add_to_database(**arguments, database='vk', groupname=groupname)
    data = vk_sql.get_from_database(**arguments, database='vk', groupname=groupname)
    parser.create_json(path_to_group, data)
