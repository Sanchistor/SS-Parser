FROM python:3.11

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt
RUN pip install playwright && playwright install chromium

CMD ["python", "bot.py"]
