"""
This sample demonstrates loading a named environment configuration profile and
programmatically overriding its values.
"""

import asyncio
from pathlib import Path

from temporalio.client import Client
from temporalio.envconfig import ClientConfig


async def main():
    """
    Demonstrates loading a named profile and overriding values programmatically.
    """
    print("--- Loading 'staging' profile with programmatic overrides ---")

    config_file = Path(__file__).parent / "config.toml"
    profile_name = "staging"

    print("The 'staging' profile in config.toml has an incorrect address (localhost:9999).")
    print("We'll programmatically override it to the correct address.")

    # Load the 'staging' profile.
    connect_config = ClientConfig.load_client_connect_config(
        profile=profile_name,
        config_file=str(config_file),
    )

    # Override the target host to the correct address.
    # This is the recommended way to override configuration values.
    connect_config["target_host"] = "localhost:7233"

    print(f"\nLoaded '{profile_name}' profile from {config_file} with overrides.")
    print(f"  Address: {connect_config.get('target_host')} (overridden from localhost:9999)")
    print(f"  Namespace: {connect_config.get('namespace')}")

    print("\nAttempting to connect to client...")
    try:
        await Client.connect(**connect_config)  # type: ignore
        print("✅ Client connected successfully!")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")


if __name__ == "__main__":
    asyncio.run(main())
