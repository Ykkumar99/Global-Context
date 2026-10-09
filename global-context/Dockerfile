FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python -m gcx setup
EXPOSE 8000
CMD ["python", "-m", "gcx", "serve", "--port", "8000", "--host", "0.0.0.0"]
