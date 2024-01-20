FROM python:3.11.4-slim-buster
LABEL authors="Sergey Petrin"

ENV POETRY_HOME=/opt/poetry
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY . /app
WORKDIR /app

RUN pip install --upgrade pip
RUN python install-poetry.py --version 1.5.1

RUN $POETRY_HOME/bin/poetry export -f requirements.txt --output ./requirements.txt
RUN pip install -r ./requirements.txt

RUN python manage.py migrate
