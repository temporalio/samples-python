import json

import boto3
from botocore.config import Config
from temporalio import activity

config = Config(region_name="us-west-2")


class BedrockActivities:
    def __init__(self) -> None:
        self.bedrock = boto3.client(service_name="bedrock-runtime", config=config)

    @activity.defn
    def prompt_bedrock(self, prompt: str) -> str:
        # model params
        modelId = "meta.llama2-70b-chat-v1"
        accept = "application/json"
        contentType = "application/json"
        max_gen_len = 512
        temperature = 0.1
        top_p = 0.2

        body = json.dumps(
            {
                "prompt": prompt,
                "max_gen_len": max_gen_len,
                "temperature": temperature,
                "top_p": top_p,
            }
        )

        response = self.bedrock.invoke_model(
            body=body, modelId=modelId, accept=accept, contentType=contentType
        )

        response_body = json.loads(response.get("body").read())

        return response_body.get("generation")
