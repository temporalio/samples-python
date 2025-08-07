"""
This sample demonstrates loading a named environment configuration profile and
overriding its values with environment variables.
"""

import asyncio
from pathlib import Path

from temporalio.client import Client
from temporalio.envconfig import ClientConfig


async def main():
    """
    Demonstrates loading a named profile and overriding it with env vars.
    """
    print("--- Loading 'staging' profile with environment variable overrides ---")

    config_file = Path(__file__).parent / "config.toml"
    profile_name = "staging"

    # In a real application, these would be set in your shell or deployment
    # environment (e.g., `export TEMPORAL_ADDRESS=localhost:7233`).
    # For this sample, we pass them as a dictionary to demonstrate.
    override_env = {
        "TEMPORAL_ADDRESS": "localhost:7233",
    }
    print("The 'staging' profile in config.toml has an incorrect address.")
    print("Using mock environment variables to override and correct it:")
    for key, value in override_env.items():
        print(f"  {key}={value}")

    # Load the 'staging' profile and apply environment variable overrides.
    connect_config = ClientConfig.load_client_connect_config(
        profile=profile_name,
        config_file=str(config_file),
        override_env_vars=override_env,
    )

    print(f"\nLoaded '{profile_name}' profile from {config_file} with overrides.")
    print(f"  Address: {connect_config.get('target_host')}")
    print(f"  Namespace: {connect_config.get('namespace')}")
    print(
        "\nNote how the incorrect address from the file was corrected by the env var."
    )

    print("\nAttempting to connect to client...")
    try:
        await Client.connect(**connect_config)  # type: ignore
        print("✅ Client connected successfully!")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")


if __name__ == "__main__":
    asyncio.run(main())
