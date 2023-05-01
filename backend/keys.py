from json import load
from pymysql.constants import CLIENT


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
