[![CI](https://github.com/b1r3k/python-poetry-boilerplate/actions/workflows/ci.yaml/badge.svg)](https://github.com/b1r3k/python-poetry-boilerplate/actions/workflows/ci.yaml)

# Voicetyping

## Requirements

## How to install

### Install gnome extension

   $ cd extension
   $ make install

You probably will need to restart your GNOME session i.e. logout/login

### Install python backend

1. Build python wheel and install it in the system

   $ poetry build

   Building voicetyping (0.2.1)
   Building sdist
   - Building sdist
   - Built voicetyping-0.2.1.tar.gz
   Building wheel
   - Building wheel
   - Built voicetyping-0.2.1-py3-none-any.whl

   $ pip3.12 install dist/voicetyping-0.2.1-py3-none-any.whl

   $ which voicetyping-server

Backend uses python-uinput for simulating keyboard from text transcript. On many linux systems `/dev/uinput` file is forbidden to be accessed without root priviliges.

   $ ls -lau /dev/input
   crw------- 1 root root 10, 223 Jul 27 14:47 /dev/uinput

On the other hand it's bit problematic to give random application access to root therefore I prefer to use group `input` and give it write permissions to `/dev/uinput` device. Therefore my advice is to use following setup:

1. Create user who will run python backend: `sudo useradd -G input,audio -M -r voicetyping`
1. Allow input group write to `/dev/uinput` by creating `/etc/udev/rules.d/99-uinput.rules` with following contents:

```
KERNEL=="uinput", GROUP="input", MODE="0660"
```

1. sudo udevadm control --reload-rules
1. sudo udevadm trigger

   $ ls -lau /dev/input
   crw-rw---- 1 root input 10, 223 Jul 27 14:47 /dev/uinput

1. Use template for DBus permissions so that extension can communicate with backend via system DBus: `sudo cp etc/voicetyping-dbus-policy.conf /etc/dbus-1/system.d/voicetyping.conf`
1. Reload DBus configuration: `sudo systemctl reload dbus`
1. Use template for systemd service: `sudo cp etc/voicetyping.service /etc/systemd/system/voicetyping@voicetyping.service`
1. Adjust paths in `/etc/systemd/system/voicetyping@voicetyping.service`
1. Enable service to run as voicetyping user: `sudo systemctl enable voicetyping@voicetyping.service`
1. Finally, start the service: `sudo systemctl start voicetyping@voicetyping.service`

**Security warning** it's important to keep access to /dev/uinput very selective both for write and read since that's how malware could get access to whatever user is typing
