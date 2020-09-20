FROM python:3.7-slim-buster

COPY requirements.txt /
COPY constraints.txt /
RUN pip install -c constraints.txt -r requirements.txt

COPY src /app/src

WORKDIR /app
CMD ["python","src/main.py"]