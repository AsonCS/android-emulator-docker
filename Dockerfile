FROM ubuntu:24.04

LABEL maintainer="Ason CS"

WORKDIR /app

COPY ./app /app
RUN chmod -R 777 /app
COPY ./root/sdk/android /root/sdk/android
RUN chmod -R 777 /root/sdk/android

#============================================
# Install Dependences
#============================================
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    openjdk-21-jdk-headless \
    libpulse0 \
    libgles2 \
    xvfb \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean;


#============================================
# Python dependencies
#============================================
RUN pip3 install --no-cache-dir --break-system-packages -r ./requirements.txt


#============================================
# Env vars
#============================================
ENV API_PORT=80
ENV DISPLAY=:99

ENV ANDROID_API_VERSION="34"
ENV ANDROID_BUILD_TOOLS="34.0.0"
ENV ANDROID_CMD="commandlinetools-linux-14742923_latest.zip"
ENV EMULATOR_ARCH="x86_64"
ENV EMULATOR_DEVICE="medium_tablet"
ENV EMULATOR_NAME="tablet"
ENV EMULATOR_PORT="5554"
ENV EMULATOR_SERIAL="emulator-${EMULATOR_PORT}"
ENV EMULATOR_TARGET="default"

ENV ANDROID_HOME="/root/sdk/android"
ENV ANDROID_AVD_HOME="$ANDROID_HOME/.android/avd"
ENV ANDROID_SDK_ROOT=$ANDROID_HOME

ENV ANDROID_PATH_BUILD_TOOLS="$ANDROID_HOME/build-tools/$ANDROID_BUILD_TOOLS"
ENV ANDROID_PATH_CMDLINE_TOOLS="$ANDROID_HOME/cmdline-tools/latest/bin"
ENV ANDROID_PATH_EMULATOR="$ANDROID_HOME/emulator"
ENV ANDROID_PATH_PLATFORM_TOOLS="$ANDROID_HOME/platform-tools"

ENV PATH="$PATH:$ANDROID_PATH_BUILD_TOOLS:$ANDROID_PATH_CMDLINE_TOOLS:$ANDROID_PATH_EMULATOR:$ANDROID_PATH_PLATFORM_TOOLS"


#============================================
# Application code
#============================================
EXPOSE 5554 5555 80

HEALTHCHECK --interval=10s --retries=30 --start-period=5m --timeout=3s \
  CMD curl -f http://localhost/emulator/status || exit 1

CMD ["./entrypoint.sh"]


#============================================
# Application code
#============================================
# docker build -t android-emulator-docker:$(date "+%Y%m%d%H%M%S") .
# docker run -d --rm --privileged --name android-emulator-docker -p 8000:80 android-emulator-docker:<tag>
# docker tag android-emulator-docker:<tag> ghcr.io/agilecontent/adm-devicecontrol:<tag>
# docker push ghcr.io/agilecontent/adm-devicecontrol:<tag>

# ============================================================================================================================

# docker build -t android-emulator-docker .
# docker run -d --rm --privileged --name android-emulator-docker -p 5555:5555 -p 5554:5554 -p 8000:80 android-emulator-docker
# docker run -d --privileged --name android-emulator-docker -p 8000:80 -v ./app:/app -v ./root/sdk/android:/root/sdk/android android-emulator-docker tail -f /dev/null
# docker exec -u root -t -i android-emulator-docker /bin/bash

# docker build --no-cache --progress=plain --target base -t android-emulator-docker-base .
# docker run -d --privileged --name android-emulator-docker-base android-emulator-docker-base
# docker exec -u root -t -i android-emulator-docker-base /bin/bash
# docker build --no-cache --progress=plain -t android-emulator-docker .
# docker run -d --privileged --name android-emulator-docker -p 5555:5555 -p 5554:5554 -p 8000:8000 android-emulator-docker
# docker run -d --privileged --name android-emulator-docker -p 5555:5555 -p 5554:5554 -p 8000:8000 android-emulator-docker tail -f /dev/null
# docker run -d --privileged --name android-emulator-docker -p 5555:5555 -p 5554:5554 -p 8000:8000 -v ./app:/app android-emulator-docker tail -f /dev/null
# docker exec -u root -t -i android-emulator-docker /bin/bash
