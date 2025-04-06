FROM python:3-slim

EXPOSE 8000

WORKDIR /data

RUN apt-get -y update && apt-get install -y --no-install-recommends \
  git \
  && rm -rf /var/lib/apt/lists/*

RUN --mount=source=.,target=.,rw pip install .[server]

CMD [ "hypercorn", "epaper_image_display_server.api:app", "--bind", "0.0.0.0:8000" ]
