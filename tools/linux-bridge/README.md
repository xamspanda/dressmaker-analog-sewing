# Linux bridge (fallback)

Only needed if, on Linux/Proton, the mod's log says `No analog keyboard found` even though
the keyboard is plugged in. The bridge runs natively on Linux, reads the Wooting
keyboard's analog interface from `/dev/hidraw*`, and sends the key depth to the mod
over UDP `127.0.0.1:47613`. The mod switches to it automatically.

Requirements: Python 3 and read access to the keyboard's hidraw devices (Wooting's udev
rules give you this).

## Run it with the game

Set the Steam launch options to:

    WINEDLLOVERRIDES="winhttp=n,b" /path/to/with-bridge.sh %command%

This starts the bridge with the game and stops it when you quit. It logs to
`~/.local/state/dressmaker-bridge.log`.

## Run it by hand

    ./wooting-bridge.py --show     # live depth meter
    ./wooting-bridge.py --debug    # log the keyboard's own press/release events
    ./wooting-bridge.py --key f    # stream a different key (match the mod's SewKey)

Supports both Wooting analog protocols: usage page 0xFF54 (older firmware) and 0xFF53
(firmware 2.50+).
