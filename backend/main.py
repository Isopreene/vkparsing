import json, os, re, pymysql, vk_api, requests
from datetime import datetime, date
from time import perf_counter
from twocaptcha import TwoCaptcha
from functools import wraps
import work_with_photos
from itertools import chain
from time import sleep


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
    def captcha_handler(captcha, **kwargs):
        """Обрабатывает капчу"""
        solver = TwoCaptcha(**kwargs)
        with open('captcha.jpg', 'wb') as file:
            file.write(requests.get(captcha.get_url(), stream=True).content)
        obj = solver.normal('captcha.jpg')
        if os.path.isfile('captcha.jpg'):
            os.remove('captcha.jpg')
        return captcha.try_again(obj['code'])  # Просим вк попробовать еще раз вместе с решенной каптчей

    def vk_login(self, groupname, **kwargs):
        """логинится в vk, заходит в группу groupname и получает все посты в виде словаря"""
        try:
            sleep(0.5)
            vk_session = vk_api.VkApi(**kwargs, captcha_handler=self.captcha_handler)
            vk = vk_session.get_api()
            id_ = re.search(r'((public)|(club))(\d+)', groupname)
            short_name = re.search(r'(\w+)', groupname)
            sleep(0.5)
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
    def create_json(groupname, data):  # на данный момент не используется
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
        elif attachment_type == 'doc':
            doc = attachment['doc']
            post_obj.add_attachment('doc', doc['url'])
        elif attachment_type == 'poll':
            poll = attachment['poll']
            post_obj.add_attachment('poll', f"vk.com/poll-{-int(poll.get('owner_id'))}_{poll.get('id')}")
        else:
            pass

    def make_posts(self):
        """Проходит по списку постов, полученному из парсера, и создаёт объекты класса Post, занося их в список PostHandler().__processed_post"""
        for post in self.data['items']:  # проходимся по dict и получаем list
            #print(*post.items(), sep='\n')
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

class ToDatabase:

    def __init__(self, data_from_post_handler=None):
        """Получает данные в виде списка объектов класса Post и заносит их в базу данных. Проверяет на хэши, если такой уже есть в БД, то не заносит"""
        self.__posts = data_from_post_handler



    @staticmethod
    def create_database(**kwargs):
        """создаёт` базу данных, куда будем записывать всё"""
        try:
            with pymysql.connect(**kwargs) as connection:
                with connection.cursor() as cursor:
                    cursor.execute('show databases')
                    if ('vk',) not in cursor:
                        cursor.execute('create database vk')
        except Exception as e:
            raise e

    @staticmethod
    def create_table(groupname, **kwargs):
        """Создаёт таблицу с именем groupname в базе данных database, если её там ещё нет"""
        try:
            with pymysql.connect(**kwargs) as connection:
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

    def add_to_database(self, groupname, **kwargs):
        """добавляет объекты класса Post в существующую таблицу в бд,
        если их там ещё нет"""
        try:
            with pymysql.connect(**kwargs) as connection:
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
                            print(attachments)
                            for attachment_type, attachment_list in [i for i in attachments.items() if i[1]]:
                                for attachment in attachment_list:
                                    counter += 1
                                    column_name = f'attachment_{counter}'
                                    query = f"update {groupname} set {column_name} = (%s) where post_hash = %s"
                                    cursor.execute(query, [attachment, check_hash])
                            connection.commit()
        except Exception as e:
            raise e

class FromDatabase:

    @staticmethod
    def get_from_database(groupname, date_start, date_finish, **kwargs):
        """Получает данные из дб database, таблицы groupname, с указанием даты старта date_start и даты финиша date_finish"""
        if not date_start:
            date_start = date(year=1, month=1, day=1)
        if not date_finish:
            date_finish = datetime.now()
        try:
            with pymysql.connect(**kwargs) as connection:
                with connection.cursor() as cursor:
                    query = f"select post_text, post_date, post_id, is_repost, attachment_1, attachment_2, attachment_3, " \
                            "attachment_4, attachment_5, attachment_6, attachment_7, attachment_8, attachment_9, attachment_10 " \
                            f"from {groupname} " \
                            "where date(post_date) >= %s and date(post_date) <= %s " \
                            "order by post_date desc"
                    cursor.execute(query, (date_start, date_finish))
                    data = cursor.fetchall()
                    columns = ('Текст', 'Дата', 'ID', 'Репост', 'Вложение 1', 'Вложение 2', 'Вложение 3', 'Вложение 4',
                               'Вложение 5', 'Вложение 6', 'Вложение 7', 'Вложение 8', 'Вложение 9', 'Вложение 10')
                    return list({key: value for key, value in zip(columns, row) if value} for row in data)
        except Exception as e:
            raise e

    @staticmethod
    def get_tablenames(**kwargs):
        """Получает имена таблиц (групп), уже существующих в бд database"""
        try:
            with pymysql.connect(**kwargs) as connection:
                with connection.cursor() as cursor:
                    query = f'show tables'
                    cursor.execute(query)
                    names = list(map(lambda x: x[0], cursor.fetchall()))
                return names
        except Exception as e:
            raise e

    @staticmethod
    def get_group_urls(groupname, **kwargs):
        """Возвращает список ссылок на фото из дб vk, таблицы groupname,"""
        try:
            with pymysql.connect(**kwargs) as connection:
                with connection.cursor() as cursor:
                    query = f"select attachment_1, attachment_2, attachment_3, " \
                            "attachment_4, attachment_5, attachment_6, attachment_7, attachment_8, attachment_9, attachment_10 " \
                            f"from {groupname} " \
                            "order by post_date desc"
                    cursor.execute(query)
                    data = cursor.fetchall()
                    return list(filter(lambda x: x and 'userapi.com' in x, chain.from_iterable(data)))
        except Exception as e:
            raise e

    def get_all_urls(self, **kwargs):
        """При отправке запроса all или без указания групп"""
        groups = self.get_tablenames(**kwargs)
        data = [{group: self.get_group_urls(groupname=group, **kwargs)} for group in groups]
        return data

class Runners:

    @staticmethod
    def start_all(args_db, date_start=None, date_finish=None):
        """При отправке запроса all или без указания групп"""
        vk_sql = FromDatabase()
        groups = vk_sql.get_tablenames(**args_db)
        data = {group: vk_sql.get_from_database(group, date_start, date_finish, **args_db) for group in groups}
        return data

    @staticmethod
    def upload_all(token, args_db):
        vk_sql = FromDatabase()
        url_photos = vk_sql.get_all_urls(**args_db)
        photographer = work_with_photos.DownloadPhotos()
        yagent = photographer.login_to_cloud(access_token=token)
        photographer.make_files_folder(agent=yagent)
        for group in url_photos:
            for groupname, post_urls in group.items():
                for url in post_urls:
                    photographer.upload_to_cloud(agent=yagent, groupname=groupname, photo_url=url)


    @staticmethod
    def start_group(*groups_to_check, args_db, args_vk, date_start=None, date_finish=None):
        """При отправке запроса с указанием групп"""
        data = dict() #итоговый список словарей, переделать в словарь {groupname1: data1, ...}
        for group in groups_to_check: #?groups=group1,group2,group3, groups_to_check это список групп в get-запросе
            parser = MainMethods()
            collected_data = parser.vk_login(**args_vk, groupname=group)  # собрали данные из вк
            if isinstance(collected_data, vk_api.exceptions.ApiError):
                if str(collected_data) == '[15] Access denied: this wall available only for community members': # если доступ к группе закрыт
                    data.update({group: f'Доступ к группе {group} закрыт, невозможно получить данные'})
                elif str(collected_data) == '[100] One of the parameters specified was missing or invalid: owner_id is undefined': # если группа не существует
                    data.update({group: f'Группа {group} не найдена, проверьте данные'})
            else: #собираем с вк, добавляем в бд и выводим из бд
                data_converter = PostsHandler(collected_data)
                data_converter.make_posts() # из вк в список объектов класса Post
                posts = data_converter.processed_posts
                to_sql = ToDatabase(posts)
                #to_sql.create_database(**args_db)
                to_sql.create_table(**args_db, groupname=group)
                to_sql.add_to_database(**args_db, groupname=group)
                from_sql = FromDatabase()
                group_data = from_sql.get_from_database(**args_db, groupname=group, date_start=date_start, date_finish=date_finish)[:100]
                data.update({group: group_data})
        return data
