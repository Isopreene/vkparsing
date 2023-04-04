FROM python:3.11

ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5000

# установка рабочей директории в контейнере
WORKDIR /app
# копирование файла зависимостей в рабочую директорию
COPY requirements.txt .
COPY . /app
# установка зависимостей
RUN pip install -r requirements.txt
EXPOSE 5000

# копирование содержимого локальной директории src в рабочую директорию
# команда, выполняемая при запуске контейнера
# CMD [ "python", "./app.py"]
CMD [ "flask", "run" ]

# FROM python:3.7-alpine
# ENV FLASK_APP=app.py
# ENV FLASK_RUN_HOST=0.0.0.0
# ENV FLASK_RUN_PORT=5000
# RUN apk add --no-cache gcc musl-dev linux-headers

# WORKDIR /app
# COPY . .
# RUN pip install -r requirements.txt
# EXPOSE 5000
# CMD [ "flask", "run" ]