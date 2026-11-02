# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

SHLUB is a serial hub: it reads `;`-terminated messages from one serial port (written by a Spike2 experiment script via a com0com virtual port pair) and fans them out to any number of "outlets" — other serial ports (e.g. for *fixstim*) and/or TCP servers (e.g. the eye-tracker calibration process on another machine). Primary target is Windows; it also runs on Linux.

## Commands

A venv lives in `.venv` (Python 3.14 on this machine; deps: pyserial, PySimpleGUI 6, platformdirs, pytest, pyinstaller). There is no requirements.txt checked in despite the README's claim.

```
# Run the GUI app (args override and are merged with the ini config)
python shlub.py --port COM7 --outlet serial,COM8 --outlet tcp,128.120.140.66,9292

# Tests (VS Code is configured to run pytest with: . -s --log-cli-level=DEBUG)
pytest -s --log-cli-level=DEBUG
pytest test_outlet.py::test_good_serial -s --log-cli-level=DEBUG

# Build the Windows executable
pyinstaller shlub.spec
```

The README's `python serial-repeater.py ...` invocation is stale — `serial_repeater.py`'s `main()` is commented out; `shlub.py` is the entry point.

### Tests require real hardware/virtual ports

The tests are integration tests, not unit tests. They open actual serial ports defined by per-platform constants at the top of `test_outlet.py` / `test_repeater.py` (Windows: com0com pairs COM6<->COM7 and COM8<->COM9, COM99 as a known-bad port; Linux: socat-style `/home/dan/mydev/ttyV0..3`). TCP tests spin up `local_server.SingleClientServer` on 127.0.0.1:9990. Tests rely on `sleep()` timing, so they are slow and can be flaky. If those ports don't exist, the tests will fail.

## Architecture

Threads everywhere; three layers:

- **`shlub.py`** — entry point. Loads/creates `~/.shlub/config.toml` via tomlkit (keys `in_serial_port` and `outlets`, a list of `--outlet`-format strings); `--port`/`--outlet` CLI args override these and are saved back to the file. Builds a `SerialRepeater` and runs a PySimpleGUI window in a separate thread; the GUI only displays config and a log pane (a `logging.Handler` writes into the Multiline). Closing the window calls `repeater.stop()`. The window icon is an embedded base64 PNG.
- **`serial_repeater.SerialRepeater(Thread)`** — opens the input port and runs a state machine (`States` enum: NOT_CONNECTED → CONNECTING → CONNECTED → DISCONNECTING → NOT_CONNECTED; `stop()` → QUITTING → DONE). In NOT_CONNECTED it discards everything except `connect;`. On `connect;`, `connect_all()` parses outlet strings (`serial,PORT` or `tcp,HOST,PORT`), creates fresh `connect_event`/`disconnect_event` objects, starts one outlet thread each, then sleeps 1s and checks `outlet.connected`. Any failure → all outlets disconnected. In CONNECTED, each message is put into every outlet's `mailbox` queue; `disconnect;` tears down outlets. There is no feedback to the sender about connection success.
- **`outlet.Outlet(Thread)`** — base class; `run()` calls `connect()`, exits immediately if it fails, otherwise polls `mailbox` (0.1s sleep) until the shared `disconnect_event` is set, then `disconnect()`. Subclasses: `SerialOutlet` and `TCPClientOutlet`. The TCP outlet performs a handshake on connect — sends `HELLO;` and requires `OK;` back — so any TCP receiver (including the tracker-side calibration code and `local_server.py`) must implement that.
- **`serial_input_queue.SerialInputQueue`** — buffers bytes from the serial port and splits on the `;` terminator. Messages passed to outlets are raw `bytes` including the terminator.

Conventions/gotchas: outlets are constructed with `connect_event=`/`disconnect_event=` kwargs (base class pops `disconnect_event`; `connect_event` is passed but ignored). Outlet threads are single-use — a reconnect creates new `Outlet` instances. Command matching is case-insensitive on the full message (`connect;`, `disconnect;`).
