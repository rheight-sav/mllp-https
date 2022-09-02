# Start by building the application with a complete image
FROM python:3.7-stretch AS build
LABEL Mantainer="tiagoepr"

# Install the package
RUN pip install mllp-https

# Now copy it into our base image.
# "Distroless" images contain only your application and its runtime dependencies. They do not contain package managers, shells or any other programs you would expect to find in a standard Linux distribution with the advantages of being much smaller.
FROM gcr.io/distroless/python3-debian10
LABEL Mantainer="tiagoepr"

ENV PYTHONPATH=/usr/local/lib/python3.7/site-packages

RUN python -c "import os; os.makedirs('/usr/local/bin', exist_ok=True); os.symlink('/usr/bin/python', '/usr/local/bin/python')"

COPY ./ssl /usr/local/lib/python3.7/site-packages/mllp_http_https/ssl
COPY --from=build /usr/local/lib/python3.7/site-packages /usr/local/lib/python3.7/site-packages

COPY --from=build /usr/local/bin/http2mllp /usr/local/bin/http2mllp
COPY --from=build /usr/local/bin/mllp2http /usr/local/bin/mllp2http
COPY --from=build /usr/local/bin/https2mllp /usr/local/bin/https2mllp
COPY --from=build /usr/local/bin/mllp2https /usr/local/bin/mllp2https

ENTRYPOINT [ ]

##################

# Alpine does not support SSL library
#FROM python:3.7-alpine AS build


#LABEL Mantainer="tiagoepr"
#
#RUN apk add --no-cache bash shadow
##RUN apk add \
##      --no-cache \
##      --repository http://dl-cdn.alpinelinux.org/alpine/v3.14/main \
##      ca-certificates
##ENV PYTHONPATH=/usr/local/lib/python3.7/site-packages
#
#WORKDIR /usr/local/lib/python3.7/site-packages/mllp_http_https
#
#COPY ./ssl /usr/local/lib/python3.7/site-packages/mllp_http_https/ssl
#
## RUN pip install ssl
#RUN python -m pip install --upgrade pip setuptools wheel
#RUN pip install mllp-https

###########################
