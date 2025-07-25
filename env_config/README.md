# Temporal External Client Configuration Samples

This directory contains Python samples that demonstrate how to use the Temporal SDK's external client configuration feature. This feature allows you to configure a `temporalio.client.Client` using a TOML file and/or environment variables, decoupling connection settings from your application code.

## Prerequisites

To run these samples successfully, you must have a local Temporal development server running. You can start one easily using `temporal server start-dev`.

## Configuration File

The `config.toml` file defines three profiles for different environments:

-   `[profile.default]`: A working configuration for local development.
-   `[profile.staging]`: A configuration with an intentionally **incorrect** address (`localhost:9999`) to demonstrate how it can be corrected by an override.
-   `[profile.prod]`: A non-runnable, illustrative-only configuration showing a realistic setup for Temporal Cloud with placeholder credentials. This profile is not used by the samples but serves as a reference.

## Samples

The following Python scripts demonstrate different ways to load and use these configuration profiles. Each runnable sample highlights a unique feature.

### `load_default.py`

This sample shows the most common use case: loading the `default` profile from the `config.toml` file.

**To run this sample:**

```bash
python3 env_config/load_default.py
```

### `load_profile.py`

This sample demonstrates loading the `staging` profile by name (which has an incorrect address) and then correcting the address using an environment variable. This highlights how environment variables can be used to fix or override file-based configuration.

**To run this sample:**

```bash
python3 env_config/load_profile.py
```

## Running the Samples

You can run each sample script directly from the root of the `samples-python` repository. Ensure you have the necessary dependencies installed by running `pip install -e .` (or the equivalent for your environment). 