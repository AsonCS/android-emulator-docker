FROM android-emulator-docker-base

WORKDIR /home/ubuntu/app
RUN chown -R ubuntu:ubuntu /home/ubuntu

USER ubuntu


#============================================
# Env vars
#============================================
ENV API_PORT=80


#============================================
# Application code
#============================================
HEALTHCHECK \
  CMD curl -f http://localhost || exit 1

EXPOSE 80

COPY --chown=ubuntu:ubuntu ./app .

LABEL maintainer="Ason CS"
LABEL org.opencontainers.image.description="Android Emulator Docker"

CMD ["./entrypoint.sh"]
