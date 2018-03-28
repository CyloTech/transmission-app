FROM alpine:3.7

RUN \
    addgroup -S transmission -g 1000 && \
    adduser -D -S -h /home/transmission -s /sbin/nologin -G transmission transmission -u 1000 && \
    apk add --no-cache \
    supervisor \
    bash \
    ca-certificates \
    curl \
    transmission-cli \
    transmission-daemon \
    transmission-doc \
    transmission-lang \
    libcap

RUN setcap cap_net_bind_service=+ep /usr/bin/transmission-daemon
ADD sources /sources
ADD sources/supervisord.conf /etc/supervisord.conf
ADD scripts/start.sh /scripts/start.sh
RUN chmod -R +x /scripts

EXPOSE 80

CMD [ "/scripts/start.sh" ]