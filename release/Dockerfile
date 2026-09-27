FROM repo.cylo.net/transmission@sha256:dec1ad496b060c70785d8275b434f02bfe47217bed37e4c04bf011c9dc3893fd

COPY select-peer-port.py /scripts/select-peer-port.py
COPY preserve-settings.py /tmp/preserve-settings.py
RUN python3 /tmp/preserve-settings.py && rm /tmp/preserve-settings.py

CMD ["python3", "/scripts/select-peer-port.py"]
