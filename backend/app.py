from flask import Flask, render_template, request

import main
import keys
from celery import Celery
from celery.schedules import crontab
from celery.utils.log import get_task_logger

def make_celery(app):
    #Celery configuration
    app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
    app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'
    app.config['CELERYBEAT_SCHEDULE'] = {
        'periodic_task-every-hour': {
            'task': 'periodic_task',
            'schedule': crontab(hour='*')
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


arguments_db = keys.KeysFromFiles().get_db()
arguments_vk = keys.KeysFromFiles().get_vk() #данные для вк
arguments_captcha = keys.KeysFromFiles().get_captcha() #данные для решения капчи
arguments_cloud = keys.KeysFromFiles().get_cloud


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
