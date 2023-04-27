import json
import os
import re
from datetime import datetime, date
from time import perf_counter
import pymysql
from pymysql.constants import CLIENT
import vk_api
from twocaptcha import TwoCaptcha
from functools import wraps
import requests
import yadisk


arguments = {'host': '37.140.192.188', 'port': 3306, 'user': 'u2003667_vk',
             'password': '1T4zDELcUYa6h7yb', 'database': 'u2003667_default',
             "client_flag": CLIENT.MULTI_STATEMENTS}  # данные сервера на хостинге
directory = "/var/www/u1234567/data//www/vkparser.site"  # поменять


class MeasureTime:
    def __init__(self, cls):
        self.cls = cls

    def __call__(self, *args, **kwargs):
        return self.cls(*args, **kwargs)

    def __getattribute__(self, name):
        attr = super().__getattribute__(name)
        if callable(attr):
            @wraps(attr)
            def wrapped(*args, **kwargs):
                start_time = perf_counter()
                result = attr(*args, **kwargs)
                end_time = perf_counter()
                print(f"Time taken to execute {attr.__name__}: {end_time - start_time} seconds")
                return result

            return wrapped
        return attr


class MainMethods:
    """Основные методы для работы в программе"""

    @staticmethod
    def captcha_handler(captcha):
        """Обрабатывает капчу"""
        config = {
            'server': 'rucaptcha.com',
            'apiKey': '9b74cd2841f2e078d5e8e21cff3df6d8',
            'defaultTimeout': 120,
            'recaptchaTimeout': 600,
            'pollingInterval': 10,
        }
        solver = TwoCaptcha(**config)
        with open('captcha.jpg', 'wb') as file:
            file.write(requests.get(captcha.get_url(), stream=True).content)
        obj = solver.normal('captcha.jpg')
        return captcha.try_again(obj['code'])  # Просим вк попробовать еще раз вместе с решенной каптчей

    def vk_login(self, groupname):
        """логинится в vk, заходит в группу groupname и получает все посты в виде словаря"""
        try:
            vk_session = vk_api.VkApi(token='fbd44e02fbd44e02fbd44e022ff8c62d19ffbd4fbd44e029807b26b8f927d40b91c66a9',
                                      captcha_handler=self.captcha_handler)
            vk = vk_session.get_api()
            id_ = re.search(r'((public)|(club))(\d+)', groupname)
            short_name = re.search(r'(\w+)', groupname)
            if id_:
                posts = vk.wall.get(owner_id=-int(id_.group(4)), count=100,
                                    filter='all')  # dict, получаем все посты, count * 25 = их количество
            elif short_name:
                posts = vk.wall.get(domain=short_name.group(1), count=100,
                                    filter='all')  # dict, получаем все посты, count * 25 = их количество
            else:
                return 'Неверно введён адрес или id сообщества'
            return posts
        except Exception as e:
            return e

    @staticmethod
    def create_group(directory, groupname):
        """Создаёт папку с именем группы groupname в корне программы"""
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
    def create_json(groupname, data):  # не нужен, работает без него
        """Создаёт json-файл и загружает его в корень папки с картинками. На данный момент не используется"""
        with open(f'{groupname}.json', 'w') as file:
            file.write('[')
            for row in data:
                json.dump(row, file, indent=4, default=str, ensure_ascii=False)
                file.write(',\n')
            file.write(']')


class Post:

    def __init__(self):
        """Превращает пост в объект класса Post с атрибутами вложений, id, текста, даты, отметки 'Является репостом', хэша"""
        self.__text = None
        self.__date = None
        self.__id_ = None
        self.__attachments = {'audio': [], 'video': [], 'doc': [], 'link': [], 'poll': [], 'photo': []}
        self.__is_repost = False
        self.__hash = None

    @property
    def text(self):
        """Геттер для __text"""
        return self.__text

    @text.setter
    def text(self, obj):
        """Сеттер для __text"""
        self.__text = obj

    @property
    def date(self):
        """Геттер для __date"""
        return self.__date

    @date.setter
    def date(self, obj):
        """Сеттер для __date"""
        self.__date = obj

    @property
    def id_(self):
        """Геттер для __id"""
        return self.__id_

    @id_.setter
    def id_(self, obj):
        """Сеттер для __id"""
        self.__id_ = obj

    @property
    def attachments(self):
        """Геттер для списка __attachments"""
        return self.__attachments

    def add_attachment(self, type_, obj):
        """Сеттер для списка __attachments"""
        self.__attachments[type_].append(obj)

    @property
    def hash(self):
        """Геттер для __hash"""
        return self.__hash

    @hash.setter
    def hash(self, obj):
        """Сеттер для __hash"""
        if self.hash is None:
            self.__hash = obj
        else:
            raise AttributeError('Хэш уже задан')

    @property
    def is_repost(self):
        """Геттер для __is_repost"""
        return self.__is_repost

    @is_repost.setter
    def is_repost(self, obj):
        """Сеттер для __is_repost"""
        self.__is_repost = obj

    @staticmethod
    def get_poll(poll):
        """Обрабатывает опрос, находящийся во вложении. Возвращает словарь со всем содержимым опроса"""
        poll_image = poll.get('photo')
        poll_image_url = None
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

    def __init__(self, data_from_parser):
        """обрабатывает dict всех постов, создаёт каждому посту объект класса Post и присваивает ему атрибуты для записи"""
        self.__data = data_from_parser
        self.__processed_posts = []  # список объектов класса Post, добавляем уже обработанные посты

    @property
    def data(self):
        """Геттер для __data"""
        return self.__data

    @property
    def processed_posts(self):
        """Геттер для списка __processed_posts"""
        return self.__processed_posts

    def add_processed_post(self, post):
        """Сеттер для списка __processed_posts"""
        self.__processed_posts.append(post)

    @staticmethod
    def add_attachment(attachment, post_obj):
        """Добавляет к атрибуту __attachments объекта класса Post вложения.
        Иными словами, формирует список вложений к посту"""
        attachment_type = attachment.get('type')
        if attachment_type == 'photo':
            photo = attachment['photo']
            link = max(photo['sizes'], key=lambda x: x['height'] * x['width'])['url']
            post_obj.add_attachment('photo', link)
        elif attachment_type == 'video':
            video = attachment['video']
            link = f"https://vk.com/video{video['owner_id']}_{video['id']}"  # _{video['access_key']}
            post_obj.add_attachment('video', link)
        elif attachment_type == 'link':
            link = attachment['link']
            post_obj.add_attachment('link', link['url'])
        elif attachment_type == 'audio':
            audio = attachment['audio']
            post_obj.add_attachment('audio', audio['url'])
        elif attachment_type == 'audio':
            doc = attachment['doc']
            post_obj.add_attachment('doc', doc['url'])
        elif attachment_type == 'poll':
            poll = attachment['poll']
            post_obj.add_attachment('doc', post_obj.get_poll(poll))
        else:
            pass

    @staticmethod
    def download_photo_local(attachment, directory):
        """Скачивает фото поста в папку directory на локальную машину"""
        if attachment.get('type') == 'photo':
            link = max(attachment['photo']['sizes'], key=lambda x: x['height'] * x['width'])['url']
            response = requests.get(link)
            pattern = max(re.search(r'uniq_tag=(-?\w+)-?(\w+)?-?(\w+)?&?', response.url).groups(),
                          key=lambda x: len(x) if x else 0)[:10]
            filename = f"{pattern}.jpg"
            if not os.path.exists(f'{directory}/{filename}'):
                with open(f'{directory}/{filename}', 'wb') as file:
                    file.write(response.content)

    def main(self):
        """Проходит по списку постов, полученному из парсера, и создаёт объекты класса Post, занося их в список PostHandler().__processed_post"""
        for post in self.data['items']:  # проходимся по dict и получаем list
            new_post = Post()
            new_post.hash = post['hash']
            new_post.date = datetime.fromtimestamp(post['date']).strftime('%Y-%m-%d %H:%M:%S')

            if post.get('copy_history'):  # если репост
                new_post.is_repost = True
                post = post['copy_history'][0]

            new_post.text = post['text']
            new_post.id_ = post['owner_id']
            attachments = post['attachments']
            for attachment in attachments:
                self.add_attachment(attachment, new_post)
            self.add_processed_post(new_post)


class MySQLHandler:

    def __init__(self, data_from_post_handler=None):
        """Получает данные в виде списка объектов класса Post и заносит их в базу данных. Проверяет на хэши, если такой уже есть в БД, то не заносит"""
        self.__posts = data_from_post_handler

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

    @staticmethod
    def create_database(host, user, password, port, client_flag):
        """создаёт` базу данных, куда будем записывать всё"""
        try:
            with pymysql.connect(host=host, user=user, password=password, port=port, client_flag=client_flag) as connection:
                with connection.cursor() as cursor:
                    cursor.execute('show databases')
                    if ('vk',) not in cursor:
                        cursor.execute('create database vk')
        except Exception as e:
            raise e

    @staticmethod
    def create_table(host, user, password, database, groupname, port, client_flag):
        """Создаёт таблицу с именем groupname в базе данных database, если её там ещё нет"""
        try:
            with pymysql.connect(host=host, user=user, password=password, port=port, database=database, client_flag=client_flag) as connection:
                with connection.cursor() as cursor:
                    cursor.execute('show tables')
                    if (groupname,) not in cursor:
                        query = f'create table {groupname}(id INT PRIMARY KEY AUTO_INCREMENT, post_hash varchar(255), ' \
                                'post_text varchar(255), post_date datetime, post_id varchar(255), is_repost bool, attachment_1 TEXT(65535), ' \
                                'attachment_2 TEXT(65535), attachment_3 TEXT(65535), attachment_4 TEXT(65535), ' \
                                'attachment_5 TEXT(65535), attachment_6 TEXT(65535), attachment_7 TEXT(65535), ' \
                                'attachment_8 TEXT(65535), attachment_9 TEXT(65535), attachment_10 TEXT(65535))'  # создали таблицу с нужными данными
                        cursor.execute(query)
        except Exception as e:
            raise e

    def add_to_database_and_download_photos(self, host, user, password, database, port, groupname, client_flag):
        """добавить объекты класса Post в существующую таблицу в бд, если их там ещё нет, а также скачать фото в папку"""
        try:
            with pymysql.connect(host=host, user=user, password=password, port=port, database=database, client_flag=client_flag) as connection:
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
                            date_ = post.date
                            is_repost = post.is_repost
                            attachments = post.attachments
                            query = f'insert into {groupname}(post_hash, post_text, post_date, post_id, is_repost) values (%s, %s, %s, %s, %s)'
                            cursor.execute(query, (check_hash, text, date_, id_,
                                                   is_repost))  # внесли текст поста, id создателя, дату поста и метку репоста (является/не является)
                            counter = 0
                            for attachment_type, attachment_list in [i for i in attachments.items() if i[1]]:
                                for attachment in attachment_list:
                                    if attachment_type == 'photo':
                                        pass
                                        """self.download_and_upload_photo(access_token='y0_AgAAAAAICbaeAAnQoQAAAADhyumQnrDWPKq4RJaNvozS0MynI_nnHew',
                                                                       groupname=groupname,
                                                                       photo_url=attachment)"""
                                    counter += 1
                                    column_name = f'attachment_{counter}'
                                    attachment_name = f'{attachment_type}: {attachment}'
                                    query = f"update {groupname} set {column_name} = (%s) where post_hash = %s"
                                    cursor.execute(query, [attachment_name, check_hash])
                            connection.commit()
        except Exception as e:
            raise e

    @staticmethod
    def get_from_database(host, user, password, database, port, groupname, date_start, date_finish, client_flag):
        """Получает данные из дб database, таблицы groupname, с указанием даты старта date_start и даты финиша date_finish"""
        if not date_start:
            date_start = date(year=1, month=1, day=1)
        if not date_finish:
            date_finish = datetime.now()
        try:
            with pymysql.connect(host=host, user=user, password=password, database=database, port=port, client_flag=client_flag) as connection:
                with connection.cursor() as cursor:
                    query = f"select post_text, post_date, post_id, is_repost, attachment_1, attachment_2, attachment_3, " \
                            "attachment_4, attachment_5, attachment_6, attachment_7, attachment_8, attachment_9, attachment_10 " \
                            f"from {groupname} " \
                            "where date(post_date) >= %s and date(post_date) <= %s " \
                            "order by post_date desc"
                    cursor.execute(query, (date_start, date_finish))
                    data = cursor.fetchall()
                    query = f'SHOW COLUMNS FROM {groupname}'
                    cursor.execute(query)
                    columns = ('Текст', 'Дата', 'ID', 'Репост', 'Вложение 1', 'Вложение 2', 'Вложение 3', 'Вложение 4',
                               'Вложение 5', 'Вложение 6', 'Вложение 7', 'Вложение 8', 'Вложение 9', 'Вложение 10')
                    return list({key: value for key, value in zip(columns, row) if value} for row in data)
        except Exception as e:
            raise e

    @staticmethod
    def get_tablenames(host, user, password, database, port, client_flag):
        """Получает имена таблиц (групп), уже существующих в бд database"""
        try:
            with pymysql.connect(host=host, user=user, password=password, database=database, port=port, client_flag=client_flag) as connection:
                with connection.cursor() as cursor:
                    query = f'show tables'
                    cursor.execute(query)
                    names = list(map(lambda x: x[0], cursor.fetchall()))
                return names
        except Exception as e:
            raise e


class Runners:

    @staticmethod
    def start_all(date_start=None, date_finish=None):
        """При отправке запроса all или без указания групп"""
        vk_sql = MySQLHandler()
        groups = vk_sql.get_tablenames(**arguments)
        data = list({group: vk_sql.get_from_database(**arguments, groupname=group,
                                                     date_start=date_start, date_finish=date_finish)}
                    for group in groups)
        return data

    @staticmethod
    def start_group(*groups_to_check, date_start=None, date_finish=None):
        """При отправке запроса с указанием групп"""
        vk_sql = MySQLHandler()
        data = list()
        parser = MainMethods()
        for group in groups_to_check:
            try:
                group_data = vk_sql.get_from_database(**arguments, groupname=group,
                                                      date_start=date_start, date_finish=date_finish)
            except pymysql.err.ProgrammingError:
                pass
            except IndexError:
                pass
            collected_data = parser.vk_login(groupname=group)
            if isinstance(collected_data, Exception):
                data.append({group: f'Доступ к группе {group} закрыт, невозможно получить данные'})
            else:
                #path_to_group = parser.create_group(directory, group)
                data_processing = PostsHandler(collected_data)
                data_processing.main()
                posts = data_processing.processed_posts
                vk_sql = MySQLHandler(posts)
                #vk_sql.create_database(**arguments)
                vk_sql.create_table(**arguments, groupname=group)
                vk_sql.add_to_database_and_download_photos(**arguments, groupname=group)
                group_data = vk_sql.get_from_database(**arguments, groupname=group, date_start=date_start, date_finish=date_finish)[:100]
                data.append({group: group_data})
        return data


#@MeasureTime
def start():
    Runners().start_group('animatron')

#print(MySQLHandler().get_tablenames(**arguments))
