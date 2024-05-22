FROM python:3.11

COPY requirements.txt /app/requirements.txt

WORKDIR /app

VOLUME /app/Files

RUN pip install -r requirements.txt

# RUN touch ~/.aws/credentials

# RUN echo "[default]\n\taws_access_key_id = <> \n\t"

COPY . .

CMD ["python3", "bot.py"]

