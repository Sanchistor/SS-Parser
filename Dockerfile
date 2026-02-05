FROM python:3.11

WORKDIR /app
COPY . .

# Install OS dependencies required by Chromium / Playwright
RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
		ca-certificates \
		libnss3 \
		libnspr4 \
		libxss1 \
		libasound2 \
		fonts-liberation \
		libatk1.0-0 \
		libatk-bridge2.0-0 \
		libcups2 \
		libxcomposite1 \
		libxrandr2 \
		libxdamage1 \
		libgbm1 \
		libgtk-3-0 \
	libpangocairo-1.0-0 \
	libgdk-pixbuf-xlib-2.0-0 \
	&& rm -rf /var/lib/apt/lists/*

RUN pip install -r requirements.txt

# Install Playwright browsers (chromium) after system deps are present
RUN pip install playwright && python -m playwright install chromium

CMD ["python", "bot.py"]
