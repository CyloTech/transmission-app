#!/usr/bin/env bash
set -x

###########################[ TRANSMISSION SETUP ]###############################

mkdir -p /torrents/downloading
mkdir -p /torrents/completed
mkdir -p /torrents/config/transmission
mkdir -p /torrents/config/log
mkdir -p /torrents/config/torrents
mkdir -p /torrents/watch

if [ ! -f /torrents/config/transmission/settings.json ]; then
    cp /sources/settings.json /torrents/config/transmission/settings.json
    sed -i "s/TR_USER/${USERNAME}/g" /torrents/config/transmission/settings.json
    sed -i "s/TR_PASS/${PASSWORD}/g" /torrents/config/transmission/settings.json
    sed -i "s/TR_PORT/${LISTENING_PORT}/g" /torrents/config/transmission/settings.json
else
    sed -i 's#"peer-port": [0-9]*,#"peer-port": '${LISTENING_PORT}',#g' /torrents/config/transmission/settings.json
fi

if [[ ${WEB_UI} == "combustion" ]]; then
    export TRANSMISSION_WEB_HOME=/opt/transmission-ui/combustion-release
elif [[ ${WEB_UI} == "transmission-web-control" ]]; then
    export TRANSMISSION_WEB_HOME=/opt/transmission-ui/transmission-web-control
elif [[ ${WEB_UI} == "kettu" ]]; then
    export TRANSMISSION_WEB_HOME=/opt/transmission-ui/kettu
fi

ls -d /torrents/* | grep -v home | xargs -d "\n" chown -R transmission:transmission

###########################[ MARK INSTALLED ]###############################

if [ ! -f /etc/app_configured ]; then
    touch /etc/app_configured
    curl -i -H "Accept: application/json" -H "Content-Type:application/json" -X POST "https://api.cylo.io/v1/apps/installed/$INSTANCE_ID"
fi

exec /bin/su --preserve-environment -s /bin/bash -c "TERM=xterm /usr/bin/transmission-daemon --foreground --config-dir /torrents/config/transmission/" transmission
