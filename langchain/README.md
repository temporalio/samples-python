# LangChain Sample

This sample shows you how you can use Temporal to orchestrate workflows for [LangChain](https://www.langchain.com). It includes an interceptor that makes LangSmith traces work seamlessly across Temporal clients, workflows and activities.

For this sample, the optional `langchain` dependency group must be included. To include, run:

    uv sync --group langchain

Export your [OpenAI API key](https://platform.openai.com/api-keys) as an environment variable. Replace `YOUR_API_KEY` with your actual OpenAI API key.

    export OPENAI_API_KEY='...'

To run, first see [README.md](../README.md) for prerequisites. Then, run the following from this directory to start the
worker:

    uv run worker.py

This will start the worker. Then, in another terminal, run the following to execute a workflow:

    uv run starter.py

Then, in another terminal, run the following command to translate a phrase:

    curl -X POST "http://localhost:8000/translate?phrase=hello%20world&language1=Spanish&language2=French&language3=Russian"

Which should produce some output like:

    {"translations":{"French":"Bonjour tout le monde","Russian":"Привет, мир","Spanish":"Hola mundo"}}

Check [LangSmith](https://smith.langchain.com/) for the corresponding trace.