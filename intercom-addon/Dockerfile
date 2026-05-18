ARG BUILD_FROM
FROM $BUILD_FROM

RUN apk add --no-cache python3 py3-aiohttp

COPY run.sh /run.sh
COPY intercom.py /intercom.py
COPY picker.html /picker.html
RUN chmod a+x /run.sh

CMD ["/run.sh"]
