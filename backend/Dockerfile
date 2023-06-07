# syntax=docker/dockerfile:1.4
FROM --platform=$BUILDPLATFORM python:3.10-alpine AS builder

WORKDIR /code

RUN apk update && apk add --no-cache gcc musl-dev linux-headers
# RUN addgroup -S docker
# RUN adduser -S --shell /bin/bash --ingroup docker vscode
# USER vscode

COPY requirements.txt /code
RUN --mount=type=cache,target=/root/.cache/pip \
    pip3 install -r requirements.txt


ENV FLASK_APP app.py
ENV FLASK_ENV development
ENV FLASK_RUN_PORT 8000
ENV FLASK_RUN_HOST 0.0.0.0
ENV FLASK_DEBUG True

EXPOSE 8000

CMD ["flask", "run"]

FROM builder AS dev-envs


# install Docker tools (cli, buildx, compose)
COPY --from=gloursdocker/docker / /

CMD ["flask", "run"]
