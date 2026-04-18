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

ENV ANDROID_HOME="/home/ubuntu/android-sdk"
ENV ANDROID_AVD_HOME="$ANDROID_HOME/.android/avd"
ENV ANDROID_SDK_ROOT=$ANDROID_HOME

ENV ANDROID_PATH_CMDLINE_TOOLS="$ANDROID_HOME/cmdline-tools/latest/bin"
ENV ANDROID_PATH_PLATFORM_TOOLS="$ANDROID_HOME/platform-tools"

ENV PATH="$PATH:$ANDROID_PATH_CMDLINE_TOOLS:$ANDROID_PATH_PLATFORM_TOOLS"


#============================================
# Application code
#============================================
HEALTHCHECK \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost')"

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
