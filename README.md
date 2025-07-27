[![CI](https://github.com/b1r3k/python-poetry-boilerplate/actions/workflows/ci.yaml/badge.svg)](https://github.com/b1r3k/python-poetry-boilerplate/actions/workflows/ci.yaml)

# Voicetyping

## Requirements

## Permisions for virtual keyboard

Backend uses python-uinput for simulating keyboard from text transcript. On many linux systems `/dev/uinput` file is forbidden to be accessed without root priviliges.

   $ ls -lau /dev/input
   crw------- 1 root root 10, 223 Jul 27 14:47 /dev/uinput

On the other hand it's bit problematic to give random application access to root therefore I prefer to use group `input` and give it write permissions to `/dev/uninput` file. Here are the steps to do that:

1. sudo usermod -aG input <USER>
2. create /etc/udev/rules.d/99-uinput.rules with following contents:

```
KERNEL=="uinput", GROUP="input", MODE="0660"
```

3. sudo udevadm control --reload-rules
4. sudo udevadm trigger

   $ ls -lau /dev/input
   crw-rw---- 1 root input 10, 223 Jul 27 14:47 /dev/uinput
