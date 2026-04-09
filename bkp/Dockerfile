FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    ANDROID_HOME=/opt/android-sdk \
    PATH=/opt/android-sdk/platform-tools:/opt/android-sdk/emulator:/opt/android-sdk/cmdline-tools/latest/bin:${PATH} \
    EMULATOR_SERIAL=emulator-5554 \
    AVD_NAME=test_avd \
    API_PORT=8000

# ── System dependencies ───────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.11 \
        python3-pip \
        openjdk-17-jdk-headless \
        libpulse0 \
        libgles2 \
        xvfb \
        wget \
        unzip \
    && rm -rf /var/lib/apt/lists/*

# ── Android SDK command-line tools ────────────────────────────────────────────
RUN mkdir -p "${ANDROID_HOME}/cmdline-tools" && \
    wget -q https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip \
        -O /tmp/cmdtools.zip && \
    unzip -q /tmp/cmdtools.zip -d /tmp && \
    mv /tmp/cmdline-tools "${ANDROID_HOME}/cmdline-tools/latest" && \
    rm /tmp/cmdtools.zip

# ── SDK components ────────────────────────────────────────────────────────────
RUN yes | sdkmanager --licenses && \
    sdkmanager \
        "platform-tools" \
        "emulator" \
        "platforms;android-34" \
        "system-images;android-34;google_apis;x86_64"

# ── Create AVD ────────────────────────────────────────────────────────────────
RUN echo "no" | avdmanager create avd \
        -n test_avd \
        -k "system-images;android-34;google_apis;x86_64" \
        --force

# ── Python dependencies ───────────────────────────────────────────────────────
WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# ── Application code ──────────────────────────────────────────────────────────
COPY . .
RUN chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
