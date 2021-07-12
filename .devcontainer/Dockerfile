FROM python:3.8.8-buster

RUN apt-get update

RUN apt-get install ffmpeg python3-pip -y

RUN pip3 install pylint

RUN useradd -ms /bin/bash dockerdev

USER dockerdev
WORKDIR /usr/local/bin/dockerdev