from flask import Flask, render_template, request
from os import getcwd
from json import load
from pymysql.constants import CLIENT
import main
from celery import Celery
from celery.schedules import crontab
from celery.utils.log import get_task_logger


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

def make_celery(app):
    #Celery configuration
    app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
    app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'
    app.config['CELERYBEAT_SCHEDULE'] = {
        'periodic_task-every-hour': {
            'task': 'periodic_task',
            'schedule': crontab(1)
        }
    }

    celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    TaskBase = celery.Task
    class ContextTask(TaskBase):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask
    return celery

workdir = getcwd()
arguments_db = KeysFromFiles().get_db()
arguments_vk = KeysFromFiles().get_vk() #данные для вк
arguments_captcha = KeysFromFiles().get_captcha() #данные для решения капчи
arguments_cloud = KeysFromFiles().get_cloud

# для локальной базы
# arguments_db = {'host': 'localhost', 'port': 3306, 'user': 'root', 'password': '12august', 'database': 'vk', 'client_flag': CLIENT.MULTI_STATEMENTS}
# arguments_vk = {"token": "fbd44e02fbd44e02fbd44e022ff8c62d19ffbd4fbd44e029807b26b8f927d40b91c66a9"}
# arguments_captcha = {"server": "rucaptcha.com", "apiKey": "9b74cd2841f2e078d5e8e21cff3df6d8", "defaultTimeout": 120, "recaptchaTimeout": 600, "pollingInterval": 10}
# arguments_cloud = 'y0_AgAAAAAICbaeAAnQoQAAAADhyumQnrDWPKq4RJaNvozS0MynI_nnHew'

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False
app.debug = True

logger = get_task_logger(__name__)
celery = make_celery(app)

@celery.task(name = "periodic_task")
def periodic_task():
    main.Runners.upload_all(token=arguments_cloud, args_db=arguments_db)
    logger.info("Hello! from periodic task")


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
