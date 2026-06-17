FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir pm-copilot-engine httpx

COPY main.py tools.py system_prompt.md ./

CMD ["python", "main.py"]
