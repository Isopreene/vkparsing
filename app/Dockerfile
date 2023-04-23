FROM python:3.9

ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_DEBUG=1

# установка рабочей директории в контейнере
WORKDIR /app
# копирование файла зависимостей в рабочую директорию
COPY requirements.txt requirements.txt
COPY . .
# установка зависимостей
RUN pip install -r requirements.txt
EXPOSE 5000

CMD [ "flask", "run" ]
