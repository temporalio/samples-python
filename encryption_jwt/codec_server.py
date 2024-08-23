import os
import ssl
import logging
import jwt
import grpc
from aiohttp import hdrs, web

from temporalio.api.common.v1 import Payload, Payloads
from temporalio.api.cloud.cloudservice.v1 import request_response_pb2, service_pb2_grpc
from google.protobuf import json_format
from encryption_jwt.codec import EncryptionCodec

DECRYPT_ROLES = ["admin"]

temporal_ops_address = "saas-api.tmprl.cloud:443"
if os.environ.get("TEMPORAL_OPS_ADDRESS"):
    os.environ.get("TEMPORAL_OPS_ADDRESS")


def build_codec_server() -> web.Application:
    # Cors handler
    async def cors_options(req: web.Request) -> web.Response:
        resp = web.Response()

        if req.headers.get(hdrs.ORIGIN) == "http://localhost:8080":
            logger.info("Setting CORS headers for localhost")
            resp.headers[hdrs.ACCESS_CONTROL_ALLOW_ORIGIN] = "http://localhost:8080"

        elif req.headers.get(hdrs.ORIGIN) == "https://cloud.temporal.io":
            logger.info("Setting CORS headers for cloud.temporal.io")
            resp.headers[hdrs.ACCESS_CONTROL_ALLOW_ORIGIN] = "https://cloud.temporal.io"

        allow_headers = "content-type,x-namespace"
        if req.scheme.lower() == "https":
            allow_headers += ",authorization"
            resp.headers[hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS] = "true"

        # common
        resp.headers[hdrs.ACCESS_CONTROL_ALLOW_METHODS] = "POST"
        resp.headers[hdrs.ACCESS_CONTROL_ALLOW_HEADERS] = allow_headers

        return resp

    def request_user_role(email: str) -> str:
        credentials = grpc.composite_channel_credentials(grpc.ssl_channel_credentials(
        ), grpc.access_token_call_credentials(os.environ.get("TEMPORAL_API_KEY")))

        with grpc.secure_channel(temporal_ops_address, credentials) as channel:
            client = service_pb2_grpc.CloudServiceStub(channel)
            request = request_response_pb2.GetUsersRequest()

            response = client.GetUsers(request, metadata=(
                ("temporal-cloud-api-version", os.environ.get("TEMPORAL_OPS_API_VERSION")),))

            for user in response.users:
                if user.spec.email == email:
                    return user.spec.access.account_access.role

            return ""

    def make_handler(fn: str):
        async def handler(req: web.Request):
            # Read payloads as JSON
            assert req.content_type == "application/json"
            payloads = json_format.Parse(await req.read(), Payloads())

            # Extract the email from the JWT.
            auth_header = req.headers.get("Authorization")
            namespace = req.headers.get("x-namespace")
            _bearer, encoded = auth_header.split(" ")
            decoded = jwt.decode(encoded, options={"verify_signature": False})

            # Use the email to determine if the payload should be decrypted.
            role = request_user_role(
                decoded["https://saas-api.tmprl.cloud/user/email"])
            if role.lower() in DECRYPT_ROLES:
                codec = EncryptionCodec(namespace)
                payloads = Payloads(payloads=await codec[fn](payloads.payloads))

            # Apply CORS and return JSON
            resp = await cors_options(req)
            resp.content_type = "application/json"
            resp.text = json_format.MessageToJson(payloads)
            return resp
        return handler

    # Build app
    # codec = EncryptionCodec(namespace)
    app = web.Application()
    # set up logger
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    app.add_routes(
        [
            web.post("/encode", make_handler('encode')),
            web.post("/decode",  make_handler('decode')),
            web.options("/decode", cors_options),
        ]
    )

    return app


if __name__ == "__main__":
    # pylint: disable=C0103
    ssl_context = None
    if os.environ.get("SSL_PEM") and os.environ.get("SSL_KEY"):
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.check_hostname = False
        ssl_context.load_cert_chain(os.environ.get(
            "SSL_PEM"), os.environ.get("SSL_KEY"))

    web.run_app(build_codec_server(), host="0.0.0.0",
                port=8081, ssl_context=ssl_context)
