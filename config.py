"""Config file for the training notebooks."""

from langchain_openai import AzureChatOpenAI, ChatOpenAI
from typing import Literal
import os
from pydantic import SecretStr



class Config:

    model = "gpt-4o"

    endpoint_uri = os.getenv("AZURE_OPENAI_ENDPOINT")
    resource_group= os.getenv("RG_NAME")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")


    def get_llm(self):
        """Returns llm model based on provider."""

        if not self.api_key or not self.endpoint_uri:
            raise ValueError("API key and endpoint URI must be set in environment variables.")

        llm = AzureChatOpenAI(
            azure_endpoint=self.endpoint_uri,
            api_key=SecretStr(self.api_key),
            azure_deployment=self.deployment_name,
            api_version="2024-12-01-preview",
        )

        return llm

