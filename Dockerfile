FROM ubuntu
USER root

RUN adduser --system --disabled-password --home /home/transmission --shell /sbin/nologin --group --uid 1000 transmission

RUN apt update && \
    apt install -y software-properties-common && \
    add-apt-repository -y ppa:transmissionbt/ppa && \
    apt update && \
    apt install -y \
    transmission-cli \
    transmission-daemon \
    transmission-common \
    rar \
    unrar \
    zip \
    unzip \
    libcap2-bin \
    wget \
    git \
    curl && \
    wget https://github.com/Secretmapper/combustion/archive/release.zip && \
    unzip release.zip -d /opt/transmission-ui/ && \
    rm release.zip && \
    wget https://github.com/ronggang/twc-release/raw/master/src.tar.gz && \
    mkdir /opt/transmission-ui/transmission-web-control && \
    tar -xvf src.tar.gz -C /opt/transmission-ui/transmission-web-control/ && \
    rm src.tar.gz && \
    git clone git://github.com/endor/kettu.git /opt/transmission-ui/kettu

RUN setcap cap_net_bind_service=+ep /usr/bin/transmission-daemon
ADD sources /sources
ADD sources/supervisord.conf /etc/supervisord.conf
ADD scripts/start.sh /scripts/start.sh
RUN chmod -R +x /scripts

RUN apt remove -y git software-properties-common && apt autoremove -y
RUN rm -rf /var/lib/apt/lists/*

EXPOSE 80

CMD [ "/scripts/start.sh" ]