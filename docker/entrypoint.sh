#!/bin/sh
# Sobe uma tela virtual para o Firefox rodar com interface e a expõe pelo navegador (noVNC):
#   Xvfb (tela :99) -> x11vnc (VNC só local) -> websockify/noVNC (http://localhost:6080/vnc.html)
set -e

Xvfb "$DISPLAY" -screen 0 1440x900x24 -nolisten tcp >/tmp/xvfb.log 2>&1 &

display_socket="/tmp/.X11-unix/X${DISPLAY#:}"
for _ in $(seq 1 50); do
    [ -e "$display_socket" ] && break
    sleep 0.1
done

x11vnc -display "$DISPLAY" -localhost -forever -shared -nopw -quiet -bg -o /tmp/x11vnc.log >/dev/null 2>&1
websockify --web /usr/share/novnc 6080 localhost:5900 >/tmp/novnc.log 2>&1 &

exec "$@"
