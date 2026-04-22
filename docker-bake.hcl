group "default" {
    targets = ["base", "app", "app-prod", "emulator"]
}

group "apps" {
    targets = ["base", "app", "app-prod"]
}

target "base" {
    context = "."
    dockerfile = "Dockerfile.base"
    args = {
        ANDROID_AVD_HOME            = ANDROID_AVD_HOME
        ANDROID_CMD                 = ANDROID_CMD
        ANDROID_HOME                = ANDROID_HOME
        ANDROID_PATH_CMDLINE_TOOLS  = ANDROID_PATH_CMDLINE_TOOLS
        ANDROID_PATH_PLATFORM_TOOLS = ANDROID_PATH_PLATFORM_TOOLS
    }
    tags = ["android-emulator-docker-base:latest"]
}

target "app" {
    context = "."
    dockerfile = "Dockerfile.app"
    contexts = {
        android-emulator-docker-base = "target:base"
    }
    target = "builder"
    args = {
        ANDROID_HOME                = ANDROID_HOME
        ANDROID_PATH_PLATFORM_TOOLS = ANDROID_PATH_PLATFORM_TOOLS
    }
    tags = ["android-emulator-docker-app:latest"]
}


variable "app_prod_maintainer" {
    default = "\"Ason CS\""
}
variable "app_prod_title" {
    default = "\"App - Android Emulator Docker\""
}
variable "app_prod_description" {
    default = "\"App Python and Adb only\""
}
variable "app_prod_source" {
    default = "\"https://github.com/AsonCS/android-emulator-docker\""
}
variable "app_prod_documentation" {
    default = "\"https://github.com/AsonCS/android-emulator-docker/packages\""
}
target "app-prod" {
    context = "."
    dockerfile = "Dockerfile.app"
    contexts = {
        android-emulator-docker-app = "target:app"
    }
    args = {
        ANDROID_HOME                = ANDROID_HOME
        ANDROID_PATH_PLATFORM_TOOLS = ANDROID_PATH_PLATFORM_TOOLS
    }
    tags = ["android-emulator-docker-app-prod:latest"]
    annotations = [ 
        "maintainer=${app_prod_maintainer}" ,
        "org.opencontainers.image.title=${app_prod_title}",
        "org.opencontainers.image.description=${app_prod_description}",
        "org.opencontainers.image.source=${app_prod_source}",
        "org.opencontainers.image.documentation=${app_prod_documentation}"
    ]
    labels = {
      "maintainer" = app_prod_maintainer,
      "org.opencontainers.image.title" = app_prod_title,
      "org.opencontainers.image.description" = app_prod_description,
      "org.opencontainers.image.source" = app_prod_source,
      "org.opencontainers.image.documentation" = app_prod_documentation
    }
}

target "emulator" {
    context = "."
    dockerfile = "Dockerfile.emulator"
    contexts = {
        android-emulator-docker-base = "target:base"
    }
    args = {
        ANDROID_API_VERSION                = ANDROID_API_VERSION
        ANDROID_BUILD_TOOLS = ANDROID_BUILD_TOOLS
        ANDROID_PATH_BUILD_TOOLS = ANDROID_PATH_BUILD_TOOLS
        ANDROID_PATH_EMULATOR = ANDROID_PATH_EMULATOR
        APKS = APKS
        EMULATOR_ARCH = EMULATOR_ARCH
        EMULATOR_DEVICE = EMULATOR_DEVICE
        EMULATOR_NAME = EMULATOR_NAME
        EMULATOR_TARGET = EMULATOR_TARGET
        PRIV_APKS = PRIV_APKS
    }
    tags = ["android-emulator-docker-emulator:latest"]
}

variable "ANDROID_API_VERSION" {}
variable "ANDROID_BUILD_TOOLS" {}
variable "ANDROID_CMD" {}
variable "ANDROID_HOME" {}
variable "ANDROID_AVD_HOME" {}
variable "ANDROID_PATH_BUILD_TOOLS" {}
variable "ANDROID_PATH_CMDLINE_TOOLS" {}
variable "ANDROID_PATH_EMULATOR" {}
variable "ANDROID_PATH_PLATFORM_TOOLS" {}
variable "APKS" {}
variable "EMULATOR_ARCH" {}
variable "EMULATOR_DEVICE" {}
variable "EMULATOR_NAME" {}
variable "EMULATOR_TARGET" {}
variable "PRIV_APKS" {}
