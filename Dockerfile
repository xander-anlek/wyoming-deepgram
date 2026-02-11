FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY run.py .
COPY wyoming_deepgram/ wyoming_deepgram/

EXPOSE 10300 10200

ENV DEEPGRAM_API_KEY=""
ENV STT_MODEL="nova-2"
ENV TTS_MODEL="aura-asteria-en"
ENV TTS_SAMPLE_RATE="24000"
ENV STT_PORT="10300"
ENV TTS_PORT="10200"

ENTRYPOINT ["python3", "run.py"]
