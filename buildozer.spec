[app]
title = YT-DLP Downloader
package.name = ytdlpdownloader
package.domain = org.ytdlp

source.dir = .
source.include_exts = py,png,jpg,kv,atlas

version = 1.0

requirements = python3,kivy==2.3.0,yt-dlp

orientation = portrait
fullscreen = 0

# All required permissions
android.permissions = android.permission.INTERNET,android.permission.WRITE_EXTERNAL_STORAGE,android.permission.READ_EXTERNAL_STORAGE,android.permission.MANAGE_EXTERNAL_STORAGE,android.permission.ACCESS_NETWORK_STATE,android.permission.ACCESS_WIFI_STATE

android.api = 33
android.minapi = 21

# Java 17
android.java_version = 17

android.ndk = 25b
android.sdk = 33
android.accept_sdk_license = True

android.archs = arm64-v8a, armeabi-v7a

[buildozer]
log_level = 2
warn_on_root = 1
