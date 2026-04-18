FROM android-emulator-docker-base AS base


FROM python:3.13.13-slim

ARG USERNAME=ubuntu
ARG USER_UID=1001
ARG USER_GID=$USER_UID
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME -s /bin/bash

WORKDIR /home/ubuntu/app
RUN chown -R ubuntu:ubuntu /home/ubuntu/app


#============================================
# Env vars
#============================================
# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENV API_PORT=80


#============================================
# Application code
#============================================
HEALTHCHECK \
  CMD curl -f http://localhost || exit 1

EXPOSE 80

COPY --chown=ubuntu:ubuntu --from=base /home/ubuntu/android-sdk/cmdline-tools /home/ubuntu/android-sdk/cmdline-tools
COPY --chown=ubuntu:ubuntu --from=base /home/ubuntu/android-sdk/licenses /home/ubuntu/android-sdk/licenses
COPY --chown=ubuntu:ubuntu --from=base /home/ubuntu/android-sdk/platform-tools /home/ubuntu/android-sdk/platform-tools
COPY --chown=ubuntu:ubuntu ./app ./

RUN pip3 install --no-cache-dir -r ./requirements.txt

USER ubuntu

LABEL maintainer="Ason CS"
LABEL org.opencontainers.image.description="Android Emulator Docker"

CMD ["./entrypoint.sh"]
