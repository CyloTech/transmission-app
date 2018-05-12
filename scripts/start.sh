#!/usr/bin/env bash
set -x

###########################[ SUPERVISOR SCRIPTS ]###############################

if [ ! -f /etc/app_configured ]; then
    mkdir -p /etc/supervisor/conf.d
cat << EOF >> /etc/supervisor/conf.d/transmission.conf
[program:transmission]
command=/bin/su -s /bin/bash -c "TERM=xterm /usr/bin/transmission-daemon --foreground --config-dir /torrents/config/transmission/" transmission
autostart=true
autorestart=true
priority=1
stdout_events_enabled=true
stderr_events_enabled=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
EOF
fi

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

ls -d /torrents/* | grep -v home | xargs -d "\n" chown -R transmission:transmission

###########################[ MARK INSTALLED ]###############################

if [ ! -f /etc/app_configured ]; then
    touch /etc/app_configured
    curl -i -H "Accept: application/json" -H "Content-Type:application/json" -X POST "https://api.cylo.io/v1/apps/installed/$INSTANCE_ID"
fi

exec /usr/bin/supervisord -n -c /etc/supervisord.conf
