FROM python:3.13-alpine

LABEL maintainer="add Matt, Nolan, Ben email"

COPY ./src/ /app

WORKDIR /app

ENTRYPOINT ["python3"]

CMD ["server.py"]
