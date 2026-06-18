# Google GenAI Samples

These samples demonstrate the [Temporal Google GenAI plugin](https://github.com/temporalio/sdk-python/tree/main/temporalio/contrib/google_genai), which runs the [Google Gemini SDK](https://googleapis.github.io/python-genai/) inside Temporal Workflows. Workflows construct a `TemporalAsyncClient`, and every Gemini API call — `generate_content`, tool calls, streaming, files, interactions, agents — runs as a Temporal Activity. You get durable execution, Temporal-managed retries and timeouts, and your credentials never enter the workflow or its event history.

## Samples

| Sample | Description |
|--------|-------------|
| [hello_world](hello_world) | Minimal `generate_content` call. Start here. |
| [tools](tools) | Automatic function calling: an `activity_as_tool`-wrapped activity and a plain workflow-method tool on one call. |
| [streaming](streaming) | Forward `generate_content_stream` chunks to an external subscriber via `streaming_topic` + `WorkflowStream`. |
| [chat](chat) | Multi-turn conversation with `client.chats`. |
| [structured_output](structured_output) | Typed JSON output via `response_schema` and a Pydantic model. |
| [mcp](mcp) | Give Gemini an MCP server's tools via `TemporalMcpClientSession`. |
| [files](files) | Upload a file with `client.files` and reference it in a call. *(needs a live API key)* |
| [interactions](interactions) | Stateful server-side conversations via `client.interactions`. *(needs a live API key)* |
| [agents](agents) | Managed-agent CRUD via `client.agents`. *(needs a live API key)* |
| [vertex_ai](vertex_ai) | The hello-world flow against Vertex AI (`vertexai=True`). *(needs GCP credentials)* |

## Prerequisites

1. Install dependencies:

   ```bash
   uv sync --group google-genai
   ```

   > The `google-genai` extra of `temporalio` is shipping in an upcoming release. Until then, install the SDK from the source checkout:
   >
   > ```bash
   > uv pip install -e ../sdk-python --extra google-genai --extra pydantic
   > ```

2. Configure credentials. Most samples use the Gemini Developer API and read an API key from the environment:

   ```bash
   export GOOGLE_API_KEY=...
   ```

   The [vertex_ai](vertex_ai) sample instead uses Vertex AI with Google Cloud Application Default Credentials — see its README. You can authenticate with `gcloud auth application-default login` and set `GOOGLE_CLOUD_PROJECT` (and optionally `GOOGLE_CLOUD_LOCATION`).

3. Start a [Temporal dev server](https://docs.temporal.io/cli#start-dev-server):

   ```bash
   temporal server start-dev
   ```

## Running a Sample

Each sample has two scripts. Start the Worker first, then the Workflow starter in a separate terminal:

```bash
# Terminal 1: start the Worker
uv run google_genai_plugin/<sample>/run_worker.py

# Terminal 2: start the Workflow
uv run google_genai_plugin/<sample>/run_workflow.py
```

For example, to run the tools sample:

```bash
# Terminal 1
uv run google_genai_plugin/tools/run_worker.py

# Terminal 2
uv run google_genai_plugin/tools/run_workflow.py
```

## Key Features Demonstrated

- **Durable API calls** — every Gemini call runs as an activity with configurable timeouts and retries; no credentials enter workflow history.
- **Automatic function calling** — the SDK's AFC loop runs in-workflow; tools can be durable activities (`activity_as_tool`) or plain workflow methods.
- **Streaming** — forward model chunks live to external subscribers via `WorkflowStream`.
- **Structured output** — Pydantic-typed results through the plugin's Pydantic data converter.
- **MCP integration** — register MCP servers on the worker; tool calls dispatched through per-server activities.
- **Full API surface** — chat, the Files API, the Interactions API, managed agents, and Vertex AI.

## Related

- [Temporal Google GenAI plugin docs](https://github.com/temporalio/sdk-python/tree/main/temporalio/contrib/google_genai)
- [Google Gemini SDK (`google-genai`)](https://googleapis.github.io/python-genai/)
