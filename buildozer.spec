[app]
title = Mi Punto de Venta
package.name = posapp
package.domain = org.test
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db
version = 0.1
requirements = python3,kivy==2.3.1,kivymd==1.2.0,sqlite3

orientation = portrait
osx.python_version = 3
osx.kivy_version = 1.9.1
fullscreen = 0

android.archs = arm64-v8a
android.api = 31
android.minapi = 21
android.sdk = 31
android.ndk = 25b
android.accept_sdk_license = True
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

[buildozer]
log_level = 2
warn_on_root = 1