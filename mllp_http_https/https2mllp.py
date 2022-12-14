### Added feature: HTTPS to MLLP
### By Tiago Rodrigues
### Sectra Iberia, Aug 2022
### Addapted from https://github.com/rivethealth/mllp-http
import base64
import functools
import http.server
import logging
import os
import socket
import ssl
import threading
import time
from datetime import datetime, timezone

from .mllp import send_mllp, parse_mllp

logger = logging.getLogger(__name__)

class MllpClientOptions:
    def __init__(self, keep_alive, max_messages, timeout):
        # self.address = address
        self.keep_alive = keep_alive
        self.max_messages = max_messages
        self.timeout = timeout


class MllpClient:
    def __init__(self, address, options):
        self.address = address
        self.options = options
        self.connections = []
        self.lock = threading.Lock()

    def _check_connection(self, connection):
        while not connection.closed:
            elasped = (
                connection.last_update - time.monotonic()
                if connection.last_update is not None
                else 0
            )
            remaining = self.options.keep_alive + elasped
            if 0 < remaining:
                time.sleep(remaining)
            else:
                try:
                    with self.lock:
                        self.connections.remove(connection)
                except ValueError:
                    pass
                else:
                    if self.options.keep_alive > 0:
                        # To keep the connection alive in case keep_alive is -1
                        connection.close()

    def _connect(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self.options.timeout:
            s.settimeout(self.options.timeout)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 10)
        # print(self.address)
        s.connect(self.address)
        connection = MllpConnection(s)
        if self.options.keep_alive is not None:
            thread = threading.Thread(
                daemon=False,
                target=self._check_connection,
                args=(connection,)
            )
            thread.start()
        return connection

    def send(self, data):
        with self.lock:
            try:
                connection = self.connections.pop()
            except IndexError:
                connection = None
            else:
                connection.last_update = None
        if connection is None:
            connection = self._connect()
        response = connection.send(data)
        if self.options.max_messages <= connection.message_count and self.options.max_messages >= 0:
            connection.close()
        else:
            connection.last_update = time.monotonic()
            with self.lock:
                self.connections.append(connection)
        return response


class MllpConnection:
    def __init__(self, socket):
        self.closed = False
        self.last_update = None
        self.message_count = 0
        self.socket = socket

    def close(self):
        self.close = True
        self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()
        logger.info("Disconnected from MLLP Server")
        #print("Disconnected from MLLP Server")

    def send(self, data):
        self.message_count += 1

        # To send the HL7 messages, it will make use of an MLLP parser to format the data
        # The parser will return the ACK/NACK response
        return send_mllp(self.socket, data)


class HttpsServerOptions:
    def __init__(self, timeout, content_type, certfile, keyfile, keep_alive, username, password, mllp_parser):
        self.timeout = timeout
        self.content_type = content_type
        self.certfile = certfile
        self.keyfile = keyfile
        self.keep_alive = keep_alive
        self.username = username
        self.password = password
        self.mllp_parser = mllp_parser


class Authentication:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.key = ''
        self.key = base64.b64encode(
            bytes('%s:%s' % (self.username, self.password), 'utf-8')).decode('ascii')

    def get_auth_key(self):
        return self.key


class HttpsHandler(http.server.BaseHTTPRequestHandler):
    def __init__(self, request, address, server, mllp_client,
                 content_type, timeout, keep_alive, authentication, mllp_parser):
        self.protocol_version = "HTTP/1.1"
        self.content_type = content_type
        self.mllp_client = mllp_client
        self.timeout = timeout
        self.keep_alive = keep_alive
        self.authentication = authentication
        self.mllp_parser = mllp_parser
        super().__init__(request, address, server)

    # For Authentication
    def do_AUTHHEAD(self):
        self.send_response(401)
        self.send_header('WWW-Authenticate', b'Basic realm=\"Test\"')
        self.send_header('Content-type', b'text/html')
        self.end_headers()

    # To check auth on server and client side
    def check_auth(self):
        key = self.authentication.get_auth_key()
        # print(self.headers['Authorization'])
        # print(self.headers['Content-type'])
        # print(self.headers['Date'])
        if self.headers['Authorization'] == None:
            self.do_AUTHHEAD()
            self.wfile.write(b'Authentication is required.')
            logger.info('Client did not authenticate.')
            return False
        elif self.headers['Authorization'] == 'Basic ' + str(key):
            logger.info('Client Authenticated.')
            return True
        else:
            self.do_AUTHHEAD()
            self.wfile.write(bytes(self.headers['Authorization'], "ascii"))
            self.wfile.write(b'Authentication failed: Wrong credentials.')
            logger.info('Client did not provide the correct credentials.')
            return False

    def do_POST(self):
        try:
            # Check authentication
            authentication_step = False
            if self.authentication != None:
                try:
                    # if username and password were given as argument, client should authenticate to server
                    authentication_step = self.check_auth()
                except Exception as e:
                    logger.error("Authentication error: %s", e)
            else:
                # if username and password were not given as argument, do not need to authenticate to server
                authentication_step = True

            if authentication_step:
                # Process received data
                content_length = int(self.headers["Content-Length"])  # From the received data
                data = self.rfile.read(content_length)  # Read income data
                logger.info("Message: %s bytes", len(data))
                logger.info("Received Data:\n{}".format(data))

                # Send data to MLLP Listener and get MLLP ACK response:
                response = self.mllp_client.send(data)

                # Parse the data from the MLLP response:
                #   > Remove Start block and End Block
                #   > Correct Carriage Return if needed
                if self.mllp_parser:
                    response = parse_mllp(response)

                # Prepare and send back ACK to HTTPS client
                self.send_response(200)
                self.send_header("Content-Length", len(response))
                if self.content_type:
                    self.send_header("Content-Type", self.content_type)
                    #print(self.content_type)
                if self.keep_alive is not None:
                    self.send_header("Keep-Alive", f"timeout={self.keep_alive}")
                now = datetime.now(timezone.utc)
                date = now.strftime("%a, %d %b %y %H:%M:%S %Z")
                # print(date)
                self.send_header("Date", date)
                self.end_headers()
                self.wfile.write(response)
                logger.info("Response: %s bytes", len(response))
                logger.info("Response Data: 200 Ok\n{}".format(response))

        except Exception as e:
            logger.error("HTTPS connection error: %s", e)


def serve(address, options, mllp_address, mllp_options):

    # MLLP Client for dealing with the MLLP TCP connection
    client = MllpClient(mllp_address, mllp_options)

    # If authentication is enabled, set the auth
    if options.username and options.password:
        auth = Authentication(
            username=options.username,
            password=options.password,
        )
        logger.info(
            "Authentication on server side is enabled.\nUser: {}\nPassword: {}".format(options.username, "*"*len(options.password)))
    elif os.environ.get("HTTP_AUTHORIZATION"):
        auth = os.environ["HTTP_AUTHORIZATION"]
        logger.info(
            "Authentication on server side is enabled with Environment Variable HTTP_AUTHORIZATION.")
    else:
        auth = None
        logger.warning(
            "Authentication on server side is disabled.")

    # HTTP server handler
    handler = functools.partial(
        HttpsHandler,
        content_type=options.content_type,
        keep_alive=options.keep_alive,
        timeout=options.timeout or None,
        mllp_client=client,
        authentication=auth,
        mllp_parser=options.mllp_parser,
    )


    try:
        server = http.server.ThreadingHTTPServer(address, handler)

        # >> Dealing with SSL/TLS on the HTTP server side
        # For Python > 3.7
        context = ssl.SSLContext(ssl.PROTOCOL_TLS)
        context.load_cert_chain(
            certfile=options.certfile,
            keyfile=options.keyfile,
        )
        server.socket = context.wrap_socket(
            server.socket,
            server_side=True,
        )
        # For Python < 3.2 SSLContext is not used, change it by ssl.wrap_socket:
        # server.socket = ssl.wrap_socket(
        #     server.socket,
        #     server_side=True,
        #     certfile="C:/ssl/certfile.crt",
        #     keyfile="C:/ssl/keyfile.key",
        # )

        logger.info("Listening on %s:%s", address[0], address[1])
        logger.info("Sending to %s:%s", mllp_address[0], mllp_address[1])
        print("\nListening on {}:{}".format(address[0], address[1]))
        print("Sending to {}:{}".format(mllp_address[0], mllp_address[1]))
        server.protocol_version = "HTTP/1.1"
        server.serve_forever()

    except Exception as e:
        logger.error("HTTPS connection error: %s", e)
