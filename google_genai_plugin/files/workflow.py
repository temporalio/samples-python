"""Upload a file with the Files API, then ask Gemini about it.

``client.files.upload`` runs as an activity on the worker — the file is read
there, not in the workflow — and the returned file handle is then referenced in
a ``generate_content`` call.
"""

# @@@SNIPSTART python-google-genai-files-workflow
from typing import cast

from google.genai import types
from temporalio import workflow
from temporalio.contrib.google_genai import TemporalAsyncClient


@workflow.defn
class FilesWorkflow:
    @workflow.run
    async def run(self, file_path: str, prompt: str) -> str:
        client = TemporalAsyncClient()
        uploaded = await client.files.upload(
            file=file_path,
            config=types.UploadFileConfig(mime_type="text/plain"),
        )
        contents = cast(types.ContentListUnion, [prompt, uploaded])
        response = await client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
        )
        return response.text or ""


# @@@SNIPEND
