# Temporal Python Samples

## Client Initialization Pattern

Use the `ClientConfig` pattern for client initialization to support environment-based configuration:

```python
from temporalio.client import Client
from temporalio.envconfig import ClientConfig

config = ClientConfig.load_client_connect_config()
config.setdefault("target_host", "localhost:7233")
client = await Client.connect(**config)
```

This pattern allows configuration via environment variables while providing sensible defaults.
