FROM python:3.10-alpine AS build
LABEL Mantainer="tiagoepr"

RUN apk add --no-cache bash shadow

WORKDIR /usr/local/lib/python3.10/site-packages/mllp_http_https

RUN python -m pip install --upgrade pip
RUN pip install mllp-https

COPY ./ssl /usr/local/lib/python3.10/site-packages/mllp_http_https/ssl

#CMD /bin/sh

# ENTRYPOINT [ ]

# FROM python:3.7-stretch AS build

# COPY . /tmp/mllp-https

# RUN pip install --upgrade pip
# RUN apt-get update
# RUN apt-get -y upgrade
# RUN pip install --no-cache-dir /tmp/mllp-https

# FROM gcr.io/distroless/python3-debian10

# ENV PYTHONPATH=/usr/local/lib/python3.7/site-packages

# RUN python -c "import os; os.makedirs('/usr/local/bin', exist_ok=True); os.symlink('/usr/bin/python', '/usr/local/bin/python')"

# COPY --from=build /usr/local/lib/python3.7/site-packages /usr/local/lib/python3.7/site-packages

# COPY --from=build /usr/local/bin/http2mllp /usr/local/bin/http2mllp

# COPY --from=build /usr/local/bin/mllp2http /usr/local/bin/mllp2http

# COPY --from=build /usr/local/bin/https2mllp /usr/local/bin/https2mllp

# COPY --from=build /usr/local/bin/mllp2https /usr/local/bin/mllp2https

# ENTRYPOINT [ ]