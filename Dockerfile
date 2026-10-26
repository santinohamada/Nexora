FROM python:3.10-slim

RUN apt-get update \
  && apt-get install -y --no-install-recommends curl espeak-ng \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir torch --extra-index-url https://download.pytorch.org/whl/cpu \
  && pip install --no-cache-dir -r requirements.txt

COPY app.py storage.py capture_validation.py train_lstm.py ./
COPY src/ src/
COPY models/ models/
COPY docker/api-entrypoint.sh /docker/api-entrypoint.sh
RUN sed -i 's/\r$//' /docker/api-entrypoint.sh && chmod +x /docker/api-entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/docker/api-entrypoint.sh"]
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
