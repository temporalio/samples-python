## Worker Versioning

This sample demonstrates how to use Temporal's Worker Versioning feature to safely deploy updates to workflow and activity code. It shows the difference between auto-upgrading and pinned workflows, and how to manage worker deployments with different build IDs.

The sample creates multiple worker versions (1.0, 1.1, and 2.0) within one deployment and demonstrates:
- **Auto-upgrading workflows**: Automatically and controllably migrate to newer worker versions
- **Pinned workflows**: Stay on the original worker version throughout their lifecycle
- **Compatible vs incompatible changes**: How to make safe updates using `workflow.patched`

### Steps to run this sample:

1) Run a [Temporal service](https://github.com/temporalio/samples-python/tree/main/#how-to-use).
   Ensure that you're using at least Server version 1.28.0 (CLI version 1.4.0).

2) Start the main application (this will guide you through the sample):
```bash
uv run worker_versioning/app.py
```

3) Follow the prompts to start workers in separate terminals:
   - When prompted, run: `uv run worker_versioning/workerv1.py`
   - When prompted, run: `uv run worker_versioning/workerv1_1.py`
   - When prompted, run: `uv run worker_versioning/workerv2.py`

The sample will show how auto-upgrading workflows migrate to newer workers while pinned workflows
remain on their original version.
