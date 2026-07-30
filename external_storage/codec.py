import gzip
from collections.abc import Iterable
from typing import List

from temporalio.api.common.v1 import Payload
from temporalio.converter import PayloadCodec


class CompressionCodec(PayloadCodec):
    """Gzip-based payload codec."""

    ENCODING = b"binary/gzip"

    async def encode(self, payloads: Iterable[Payload]) -> List[Payload]:
        return [
            Payload(
                metadata={"encoding": self.ENCODING},
                data=gzip.compress(p.SerializeToString()),
            )
            for p in payloads
        ]

    async def decode(self, payloads: Iterable[Payload]) -> List[Payload]:
        result: List[Payload] = []
        for p in payloads:
            if p.metadata.get("encoding") == self.ENCODING:
                result.append(Payload.FromString(gzip.decompress(p.data)))
            else:
                result.append(p)
        return result
