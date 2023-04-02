from flask import Flask, render_template, request
import main

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False


@app.route('/', methods=['get'])
def get_groups_by_get_requests():
    """Выводит все посты из указанных групп через гет-запросы"""
    groups = request.args.get('groups', None)
    all_ = request.args.get('all', None)
    date_start = request.args.get('date_start', None)
    date_finish = request.args.get('date_finish', None)
    if all_:
        data = main.Runners.start_all(date_start=date_start, date_finish=date_finish)
        return data
    elif groups:
        groups = groups.split(',')
        data = main.Runners.start_group(*groups, date_start=date_start, date_finish=date_finish)
        return data
    else:
        return f'Привет! Это парсер для групп vk.com. Пошлите get-запрос вида domain.com/?params или domain.com/params. \n\nСписок доступных параметров: groups=(через запятую), all=(True/False), date_start=(YYYY-MM-DD), date_finish=(YYYY-MM-DD)'

@app.route('/all')
def get_all_groups():
    """Выводит все посты из всех групп, записанных в базу данных"""
    data = main.Runners.start_all()
    return data


app.run()
