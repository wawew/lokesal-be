FROM python:3.6.9
MAINTAINER Your Name "firdaus@alterra.id"
RUN mkdir -p /var/api/lokesal-backend
COPY . /var/api/lokesal-backend
RUN pip install -r /var/api/lokesal-backend/requirements.txt
ENV INI_KUNCI_LOKESAL=INI_KUNCI_LOKESAL
ENV INI_EMAIL_LOKESAL=INI_EMAIL_LOKESAL
ENV INI_PWD_LOKESAL=INI_PWD_LOKESAL
ENV FLASK_ENV=FLASK_ENV
ENV INI_UNAME=INI_UNAME
ENV INI_PWD=INI_PWD
ENV INI_DB_ENDPOINT=INI_DB_ENDPOINT
ENV INI_DB_TEST=INI_DB_TEST
ENV INI_DB_DEV=INI_DB_DEV
WORKDIR /var/api/lokesal-backend
ENTRYPOINT [ "python" ]
CMD [ "app.py" ]
