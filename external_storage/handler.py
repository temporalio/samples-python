"""HTTP routes for a Temporal codec server with external storage support.

A *codec server* is an HTTP service the Temporal Web UI and CLI can call to
transform payloads on demand — typically to decode (decompress, decrypt,
fetch-from-storage) so a human can read what the workflow saw. The contract
expected by the Web UI is:

* ``POST /encode`` and ``POST /decode`` accept a JSON-encoded ``Payloads``
  protobuf message in the request body and return a transformed ``Payloads``
  message in the same format.
* ``POST /download`` is a specialized endpoint that only accepts external
  storage references and resolves them to their actual contents. Kept
  separate from ``/decode`` so the Web UI can defer fetching potentially
  large blobs until a user explicitly asks for them.

The :func:`payload_routes` factory builds these three route definitions
configured with an :class:`ExternalStorage` plus optional codec layers that
match the client's ``DataConverter`` setup."""

from typing import List, Optional

from aiohttp import web
from google.protobuf import json_format
from temporalio.api.common.v1 import Payload, Payloads
from temporalio.converter import ExternalStorage, PayloadCodec


def _is_storage_reference(payload: Payload) -> bool:
    """A payload is an external-storage reference iff it carries external_payloads metadata.

    When the SDK offloads a payload to external storage it replaces the
    in-band bytes with a small protobuf "claim check" — the ``external_payloads``
    repeated field is the marker the SDK uses to recognize it on the way back.
    """
    return len(payload.external_payloads) > 0


def payload_routes(
    external_storage: ExternalStorage,
    prestorage_codec: Optional[PayloadCodec] = None,
    poststorage_codec: Optional[PayloadCodec] = None,
) -> List[web.RouteDef]:
    """Build aiohttp routes for the codec server's /encode, /decode, and /download endpoints.

    ``external_storage`` is the external storage configured on the client's
    DataConverter and is required — without it the routes have nothing to add
    over a plain codec server.

    The codec layers are optional, and run in a defined order relative to
    external storage to mirror what the client's DataConverter does:

    * ``prestorage_codec`` — the codec configured on the client's
      DataConverter. On encode it runs BEFORE the external-storage offload
      decision, so the SDK checks whether the *transformed* bytes
      (compressed, encrypted, etc.) exceed the threshold. On decode it runs
      AFTER storage retrieval, so the codec sees the original transformed
      bytes regardless of where they came from.
    * ``poststorage_codec`` — typically only used when payloads pass through
      a proxy that wraps them with an additional codec layer outside the
      storage envelope (envelope encryption applied at a network edge, for
      example). On encode it runs after offload; on decode it runs first
      (to strip the proxy envelope before storage retrieval).

    Register the result on any :class:`aiohttp.web.Application` via
    :meth:`aiohttp.web.Application.add_routes`.
    """

    async def _decode_non_refs(payloads: List[Payload]) -> List[Payload]:
        # Storage references are claim-check protos with their own encoding —
        # they aren't bytes the codec produced, so the codec can't decode
        # them. Skip refs and only feed real payloads through the codec.
        if prestorage_codec is None:
            return payloads
        result = list(payloads)
        non_ref_idx = [
            i for i, p in enumerate(payloads) if not _is_storage_reference(p)
        ]
        decoded = await prestorage_codec.decode([payloads[i] for i in non_ref_idx])
        for i, p in zip(non_ref_idx, decoded):
            result[i] = p
        return result

    async def _read_payloads(req: web.Request) -> List[Payload]:
        assert req.content_type == "application/json"
        proto = json_format.Parse(await req.read(), Payloads())
        return list(proto.payloads)

    def _write_payloads(payloads: List[Payload]) -> web.Response:
        return web.Response(
            content_type="application/json",
            text=json_format.MessageToJson(Payloads(payloads=payloads)),
        )

    async def encode_handler(req: web.Request) -> web.Response:
        payloads = await _read_payloads(req)
        # Encode pipeline mirrors what a client-side DataConverter does:
        #   1. pre-storage codec encodes (compress / encrypt / etc.)
        #   2. external storage decides whether the transformed bytes
        #      exceed the threshold and replaces them with a reference
        #   3. post-storage codec encodes whatever ended up inline
        if prestorage_codec is not None:
            payloads = await prestorage_codec.encode(payloads)
        # ``_store_payload_sequence`` is the SDK's internal helper used by
        # DataConverter. Calling it directly lets the codec server reuse the
        # exact same offload-if-large logic the client uses, instead of
        # re-implementing the size-threshold check here. The leading
        # underscore signals it's not a stable public API.
        payloads = await external_storage._store_payload_sequence(payloads)
        if poststorage_codec is not None:
            payloads = await poststorage_codec.encode(payloads)
        return _write_payloads(payloads)

    async def decode_handler(req: web.Request) -> web.Response:
        payloads = await _read_payloads(req)
        # Decode pipeline is the encode pipeline in reverse:
        #   1. post-storage codec decodes (strip proxy envelope, if any)
        #   2. external storage retrieves any references in-band
        #   3. pre-storage codec decodes the real bytes
        if poststorage_codec is not None:
            payloads = await poststorage_codec.decode(payloads)
        # preserveStorageRefs=true is for clients that want to inspect the
        # raw references themselves (a debug view, an "audit who fetched
        # what" log, etc.). When unset, default behavior fetches from
        # storage so the user sees the payload as the workflow saw it.
        preserve_refs = req.query.get("preserveStorageRefs", "false").lower() == "true"
        if not preserve_refs:
            payloads = await external_storage._retrieve_payload_sequence(payloads)
        payloads = await _decode_non_refs(payloads)
        return _write_payloads(payloads)

    async def download_handler(req: web.Request) -> web.Response:
        # /download exists as a separate endpoint from /decode because
        # resolving an external-storage reference can be expensive (network
        # round-trip, potentially large blob). The Web UI uses /download as
        # an opt-in "click to fetch" action — keeping it off /decode's
        # auto-resolution path avoids accidentally pulling many large blobs
        # when a user simply navigates to a workflow page.
        payloads = await _read_payloads(req)
        if not all(_is_storage_reference(p) for p in payloads):
            return web.Response(
                status=400, text="all payloads must be storage references"
            )
        retrieved = await external_storage._retrieve_payload_sequence(payloads)
        decoded = await _decode_non_refs(retrieved)
        return _write_payloads(decoded)

    return [
        web.post("/encode", encode_handler),
        web.post("/decode", decode_handler),
        web.post("/download", download_handler),
    ]
