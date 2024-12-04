FROM python:3.13-alpine

COPY ./src/ /app

WORKDIR /app

ENTRYPOINT ["python3"]

CMD ["server.py"]
