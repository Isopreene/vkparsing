from flask import Flask, render_template, request
import main
#from waitress import serve
#import sys

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
        data = main.Runners.start_all(date_start=date_start, date_finish=date_finish) # список словарей
    elif groups:
        groups = groups.split(',')
        data = main.Runners.start_group(*groups, date_start=date_start, date_finish=date_finish)
    else:
        return render_template('start_page.html', host=request.host)

    return render_template('result.html', web_data=data) # web_data - список словарей

@app.route('/all')
def get_all_groups():
    """Выводит все посты из всех групп, записанных в базу данных"""
    data = main.Runners.start_all()
    return render_template('result.html', web_data=data) # web_data - список словарей


if __name__ == '__main__':
    app.run(debug=True)
    #serve(app, host='0.0.0.0', port=8000)'''
