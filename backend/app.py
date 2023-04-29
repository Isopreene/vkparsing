from flask import Flask, render_template, request
from os import getcwd
from json import load
from pymysql.constants import CLIENT

import main

class KeysFromFiles:

    def get_db(self):
        arguments = {'host': 'db', 'user': 'root', 'password': None,
                        'database': 'vk', 'client_flag': CLIENT.MULTI_STATEMENTS}
        with open('/run/secrets/db-password') as file:
            password = file.read().strip()
        arguments['password'] = password
        return arguments

    def get_vk(self):
        with open('/run/secrets/vk') as file:
            try:
                data = load(file)
                return data
            except Exception as E:
                raise E

    def get_captcha(self):
        with open('/run/secrets/captcha') as file:
            try:
                data = load(file)
                return data
            except Exception as E:
                raise E

workdir = getcwd()
arguments_db = KeysFromFiles().get_db()
arguments_vk = KeysFromFiles().get_vk() #данные для вк
arguments_captcha = KeysFromFiles().get_captcha() #данные для решения капчи


app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False
app.debug = True


@app.route('/', methods=['get'])
def get_groups_by_get_requests():
    """Выводит все посты из указанных групп через гет-запросы"""
    groups = request.args.get('groups', None)
    all_ = request.args.get('all', None)
    date_start = request.args.get('date_start', None)
    date_finish = request.args.get('date_finish', None)
    if all_:
        data = main.Runners.start_all(args_db=arguments_db, date_start=date_start, date_finish=date_finish) # список словарей
    elif groups:
        groups = groups.split(',')
        data = main.Runners.start_group(*groups, args_db=arguments_db, args_vk=arguments_vk, date_start=date_start, date_finish=date_finish)
    else:
        return render_template('start_page.html', host=request.host)
    return data

@app.route('/all')
def get_all_groups():
    """Выводит все посты из всех групп, записанных в базу данных"""
    data = main.Runners.start_all(args_db=arguments_db)  # список словарей
    return data


if __name__ == '__main__':
    app.run(debug=True)
