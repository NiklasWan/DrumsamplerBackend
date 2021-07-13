FROM python:3.8.8-buster

RUN apt-get update

RUN apt-get install ffmpeg python3-pip -y

RUN pip3 --disable-pip-version-check --no-cache-dir install pylint

COPY requirements.txt /tmp/pip-tmp/
COPY drumsamp_models-1.0-py3-none-any.whl /tmp/pip-tmp/
RUN pip3 --disable-pip-version-check --no-cache-dir install -r /tmp/pip-tmp/requirements.txt /tmp/pip-tmp/drumsamp_models-1.0-py3-none-any.whl 
RUN rm -rf /tmp/pip-tmp

RUN useradd -ms /bin/bash dockerdev

USER dockerdev
WORKDIR /usr/local/bin/dockerdev