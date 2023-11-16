FROM python:3.12-bullseye

WORKDIR /app

RUN sed -i 's/deb.debian.org/mirrors.huaweicloud.com/g' /etc/apt/sources.list

RUN apt-get update && apt-get install -y ffmpeg

COPY requirements.txt /tmp/requirements.txt

RUN pip install -r /tmp/requirements.txt

COPY . .

CMD ["tail", "-f", "/dev/null"]