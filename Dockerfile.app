# syntax=docker/dockerfile:1

FROM android-emulator-docker-base AS builder

WORKDIR /home/ubuntu/app
RUN chown -R ubuntu:ubuntu /home/ubuntu/app


#============================================
# Env vars
#============================================
ARG ANDROID_HOME
ARG ANDROID_PATH_PLATFORM_TOOLS

ENV API_PORT=80

ENV ANDROID_HOME=$ANDROID_HOME
ENV ANDROID_SDK_ROOT=$ANDROID_HOME
ENV ANDROID_PATH_PLATFORM_TOOLS=$ANDROID_PATH_PLATFORM_TOOLS

ENV PATH="$PATH:$ANDROID_PATH_PLATFORM_TOOLS"


#============================================
# Application code
#============================================
HEALTHCHECK \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost')"

EXPOSE 80

COPY --chown=ubuntu:ubuntu ./app ./

RUN pyinstaller --onefile --add-data ./static:./static main.py

USER ubuntu

RUN chmod +x ./entrypoint.sh

LABEL maintainer="Ason CS"
LABEL org.opencontainers.image.description="Android Emulator Docker"

CMD ["./entrypoint.sh"]

FROM ubuntu:24.04

#============================================
# Env vars
#============================================
ARG ANDROID_HOME
ARG ANDROID_PATH_PLATFORM_TOOLS

ENV API_PORT=80

ENV ANDROID_HOME=$ANDROID_HOME
ENV ANDROID_SDK_ROOT=$ANDROID_HOME
ENV ANDROID_PATH_PLATFORM_TOOLS=$ANDROID_PATH_PLATFORM_TOOLS

ENV PATH="$PATH:$ANDROID_PATH_PLATFORM_TOOLS"


#============================================
# Application code
#============================================
COPY --chown=ubuntu:ubuntu --from=builder /home/ubuntu/android-sdk/licenses /home/ubuntu/android-sdk/licenses
COPY --chown=ubuntu:ubuntu --from=builder /home/ubuntu/android-sdk/platform-tools /home/ubuntu/android-sdk/platform-tools
COPY --chown=ubuntu:ubuntu --from=builder /home/ubuntu/app/dist/main /home/ubuntu/app/main

RUN chmod +x /home/ubuntu/app/main

USER ubuntu

EXPOSE 80

CMD ["/home/ubuntu/app/main"]
