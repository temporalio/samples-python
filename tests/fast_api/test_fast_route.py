import asyncio

import aiohttp


def test_read_main(client):
    async def test_async():
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"http://{client.service_client.config.target_host}/"
            ) as resp:
                assert resp.status == 200
                assert await resp.text() == "Hello, World!"

        await test_async()
