from json import load
from pymysql.constants import CLIENT

#todo
"""
Раз ты уже решил собирать аргументы из файла.
То бери их все.
Причём с vk я так понимаю ты что-то подобное уже сделал

Задача: Унифицировать всё к одному типу конфигов - json

Пример как выглядит файл у vscode. Это json.
{
    "name": "My Server",
    "host": "localhost",
    "protocol": "sftp",
    "port": 22,
    "password" "1T4zDELcUYa6h7yb",
    "username": "username",
    "remotePath": "/",
    "uploadOnSave": false,
    "useTempFile": false,
    "openSsh": false
}
_________________

Далее исключи повторы (don't repeat yourself - почитай про это)
Создай метод один метод чтения файла с  аргументом пути

"""

class KeysFromFiles:

    @staticmethod
    def get_db():
        arguments = {'host': 'db', 'user': 'root', 'password': None,
                        'database': 'vk', 'client_flag': CLIENT.MULTI_STATEMENTS}
        with open('/run/secrets/db-password') as file:
            password = file.read().strip()
        arguments['password'] = password
        return arguments

    @staticmethod
    def get_vk():
        with open('/run/secrets/vk') as file:
            try:
                data = load(file)
                return data
            except Exception as E:
                raise E

    @staticmethod
    def get_captcha():
        with open('/run/secrets/captcha') as file:
            try:
                data = load(file)
                return data
            except Exception as E:
                raise E

    @staticmethod
    def get_cloud():
        with open('/run/secrets/cloud') as file:
            token = file.read().strip()
        return token
