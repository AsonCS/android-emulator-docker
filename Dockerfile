#====================================================================================================================================
# Base
#====================================================================================================================================
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
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean;


#============================================
# Python dependencies
#============================================
COPY ./app/requirements.txt /requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r /requirements.txt
RUN rm /requirements.txt


#============================================
# Args vars
#============================================
ARG ANDROID_API_VERSION
ENV ANDROID_API_VERSION=$ANDROID_API_VERSION
ARG ANDROID_BUILD_TOOLS
ENV ANDROID_BUILD_TOOLS=$ANDROID_BUILD_TOOLS
ARG ANDROID_CMD
ENV ANDROID_CMD=$ANDROID_CMD
ARG EMULATOR_ARCH
ENV EMULATOR_ARCH=$EMULATOR_ARCH
ARG EMULATOR_DEVICE
ENV EMULATOR_DEVICE=$EMULATOR_DEVICE
ARG EMULATOR_NAME
ENV EMULATOR_NAME=$EMULATOR_NAME
ARG EMULATOR_PORT
ENV EMULATOR_PORT=$EMULATOR_PORT
ARG EMULATOR_SERIAL
ENV EMULATOR_SERIAL=$EMULATOR_SERIAL
ARG EMULATOR_TARGET
ENV EMULATOR_TARGET=$EMULATOR_TARGET


#============================================
# Env vars
#============================================
ENV DISPLAY=:99

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
COPY ./root/sdk/android/.apks ./.apks

COPY ./root/sdk/android/entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh
CMD [ "tail", "-f", "/dev/null"]
# docker build --no-cache --progress=plain --target base -t android-emulator-docker-base .
# docker run -d --privileged --name android-emulator-docker-base android-emulator-docker-base
# docker exec -u root -t -i android-emulator-docker-base /bin/bash


#====================================================================================================================================
# Emulator
#====================================================================================================================================
FROM base

LABEL maintainer="Ason CS"

RUN rm -rf /root/sdk/android/.apks
RUN rm -rf /root/sdk/android/.temp
# RUN rm -rf /root/sdk/android/build-tools
# RUN rm -rf /root/sdk/android/platforms
# RUN rm -rf /root/sdk/android/system-images
RUN rm -rf /root/sdk/android/*.log

RUN mkdir -p /app
COPY ./app /app
RUN chmod -R 777 /app

WORKDIR /app


#============================================
# Env vars
#============================================
ENV API_PORT=80


#============================================
# Application code
#============================================
EXPOSE 5554 5555 8000

CMD ["./entrypoint.sh"]
# docker build --no-cache --progress=plain -t android-emulator-docker .
# docker run -d --privileged --name android-emulator-docker -p 5555:5555 -p 5554:5554 -p 8000:8000 android-emulator-docker
# docker run -d --privileged --name android-emulator-docker -p 5555:5555 -p 5554:5554 -p 8000:8000 android-emulator-docker tail -f /dev/null
# docker run -d --privileged --name android-emulator-docker -p 5555:5555 -p 5554:5554 -p 8000:8000 -v ./app:/app android-emulator-docker tail -f /dev/null
# docker exec -u root -t -i android-emulator-docker /bin/bash
