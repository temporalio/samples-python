import logging
import os
import ssl

import jwt
import requests
from aiohttp import hdrs, web
from google.protobuf import json_format
from jwt import PyJWK
from jwt.algorithms import RSAAlgorithm
from temporalio.api.cloud.cloudservice.v1 import GetUsersRequest
from temporalio.api.common.v1 import Payloads
from temporalio.client import CloudOperationsClient

from encryption_jwt.codec import EncryptionCodec

AUTHORIZED_ACCOUNT_ACCESS_ROLES = ["owner", "admin"]
AUTHORIZED_NAMESPACE_ACCESS_ROLES = ["read", "write", "admin"]

TEMPORAL_CLIENT_CLOUD_API_VERSION = "2024-05-13-00"

temporal_ops_address = (
    os.environ.get("TEMPORAL_OPS_ADDRESS") or "saas-api.tmprl.cloud:443"
)


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

    async def decryption_authorized(email: str, namespace: str) -> bool:
        client = await CloudOperationsClient.connect(
            api_key=os.environ.get("TEMPORAL_API_KEY"),
            version=TEMPORAL_CLIENT_CLOUD_API_VERSION,
        )

        response = await client.cloud_service.get_users(
            GetUsersRequest(namespace=namespace)
        )

        for user in response.users:
            if user.spec.email.lower() == email.lower():
                if (
                    user.spec.access.account_access.role
                    in AUTHORIZED_ACCOUNT_ACCESS_ROLES
                ):
                    return True
                else:
                    if namespace in user.spec.access.namespace_accesses:
                        if (
                            user.spec.access.namespace_accesses[namespace].permission
                            in AUTHORIZED_NAMESPACE_ACCESS_ROLES
                        ):
                            return True

        return False

    def make_handler(fn: str):
        async def handler(req: web.Request):
            namespace = req.headers.get("x-namespace") or "default"
            auth_header = req.headers.get("Authorization") or ""
            _bearer, encoded = auth_header.split(" ")

            # Extract the kid from the Auth header
            jwt_dict = jwt.get_unverified_header(encoded)
            kid = jwt_dict["kid"]
            algorithm = jwt_dict["alg"]

            # Fetch Temporal Cloud JWKS
            jwks_url = "https://login.tmprl.cloud/.well-known/jwks.json"
            jwks = requests.get(jwks_url).json()

            # Extract Temporal Cloud's public key
            pyjwk = None
            for key in jwks["keys"]:
                if key["kid"] == kid:
                    # Convert JWKS key to PEM format
                    pyjwk = PyJWK.from_dict(key)
                    break

            if pyjwk is None:
                raise ValueError("Public key not found in JWKS")

            # Decode the jwt, verifying against Temporal Cloud's public key
            decoded = jwt.decode(
                encoded,
                pyjwk.key,
                algorithms=[algorithm],
                audience=[
                    "https://saas-api.tmprl.cloud",
                    "https://prod-tmprl.us.auth0.com/userinfo",
                ],
            )

            # Use the email to determine if the user is authorized to decrypt the payload
            authorized = await decryption_authorized(
                decoded["https://saas-api.tmprl.cloud/user/email"], namespace
            )

            if authorized:
                # Read payloads as JSON
                assert req.content_type == "application/json"
                payloads = json_format.Parse(await req.read(), Payloads())
                encryptionCodec = EncryptionCodec(namespace)
                payloads = Payloads(
                    payloads=await getattr(encryptionCodec, fn)(payloads.payloads)
                )

            # Apply CORS and return JSON
            resp = await cors_options(req)
            resp.content_type = "application/json"
            resp.text = json_format.MessageToJson(payloads)
            return resp

        return handler

    # Build app
    app = web.Application()
    # set up logger
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    app.add_routes(
        [
            web.post("/encode", make_handler("encode")),
            web.post("/decode", make_handler("decode")),
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
        ssl_context.load_cert_chain(
            os.environ.get("SSL_PEM") or "", os.environ.get("SSL_KEY") or ""
        )

    web.run_app(
        build_codec_server(), host="0.0.0.0", port=8081, ssl_context=ssl_context
    )
