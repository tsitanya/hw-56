FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc nginx libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN rm -f /etc/nginx/sites-enabled/default
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["sh", "-c", "python -c 'from app import init_db; init_db()' && nginx && uwsgi --ini uwsgi.ini"]