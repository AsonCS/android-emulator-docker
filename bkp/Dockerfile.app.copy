FROM android-emulator-docker-base

WORKDIR /home/ubuntu
COPY ./setup_base.sh ./setup.sh

RUN chmod 777 ./setup.sh

#============================================
# Env vars
#============================================
ENV API_PORT=80

ENV ANDROID_CMD="commandlinetools-linux-14742923_latest.zip"

ENV ANDROID_HOME="/home/ubuntu/android-sdk"
ENV ANDROID_AVD_HOME="$ANDROID_HOME/.android/avd"
ENV ANDROID_SDK_ROOT=$ANDROID_HOME

ENV ANDROID_PATH_CMDLINE_TOOLS="$ANDROID_HOME/cmdline-tools/latest/bin"
ENV ANDROID_PATH_PLATFORM_TOOLS="$ANDROID_HOME/platform-tools"

ENV PATH="$PATH:$ANDROID_PATH_CMDLINE_TOOLS:$ANDROID_PATH_PLATFORM_TOOLS"


#============================================
# Configure Android SDK
#============================================
RUN ./setup.sh

EXPOSE 80

COPY ./app ./app

RUN chmod -R 777 ./android-sdk
RUN chmod -R 777 ./app

WORKDIR /home/ubuntu/app

USER ubuntu

LABEL maintainer="Ason CS"
LABEL org.opencontainers.image.description="Android Emulator Docker"

CMD ["./entrypoint.sh"]
# docker build -t=android-emulator-docker-app -f=Dockerfile.app .
# export ADB_KEY=$(cat ~/.android/adbkey)
# docker compose -f 'docker-compose.yaml' up -d --build 'app'
# docker-compose up -d --build
# docker-compose down
