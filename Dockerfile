FROM python:3.7

WORKDIR "/opt/gateway"

COPY Pipfile .
COPY Pipfile.lock .
COPY gateway/ ./gateway

RUN pip install pipenv && \
    pipenv sync

CMD ["pipenv", "run", "python", "-m", "gateway"]
