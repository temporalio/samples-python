"""
This sample demonstrates loading the default environment configuration profile
from a TOML file.
"""

import asyncio
from pathlib import Path

from temporalio.client import Client
from temporalio.envconfig import ClientConfig


async def main():
    """
    Loads the default profile from the config.toml file in this directory.
    """
    print("--- Loading default profile from config.toml ---")

    # For this sample to be self-contained, we explicitly provide the path to
    # the config.toml file included in this directory.
    # By default though, the config.toml file will be loaded from
    # ~/.config/temporalio/temporal.toml (or the equivalent standard config directory on your OS).
    config_file = Path(__file__).parent / "config.toml"

    # load_client_connect_config is a helper that loads a profile and prepares
    # the config dictionary for Client.connect. By default, it loads the
    # "default" profile.
    connect_config = ClientConfig.load_client_connect_config(
        config_file=str(config_file)
    )

    print(f"Loaded 'default' profile from {config_file}.")
    print(f"  Address: {connect_config.get('target_host')}")
    print(f"  Namespace: {connect_config.get('namespace')}")
    print(f"  gRPC Metadata: {connect_config.get('rpc_metadata')}")

    print("\nAttempting to connect to client...")
    try:
        await Client.connect(**connect_config)  # type: ignore
        print("✅ Client connected successfully!")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")


if __name__ == "__main__":
    asyncio.run(main())
