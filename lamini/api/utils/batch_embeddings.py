from typing import Any, Dict, List, Optional, Union

import aiohttp

import lamini
from lamini.api.lamini_config import get_config, get_configured_key, get_configured_url
from lamini.api.rest_requests import make_async_web_request, make_web_request


class BatchEmbeddings:

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> None:
        self.config = get_config()
        self.api_key = api_key or lamini.api_key or get_configured_key(self.config)
        self.api_url = api_url or lamini.api_url or get_configured_url(self.config)
        self.api_prefix = self.api_url + "/v1/"

    def submit(
        self,
        prompt: Union[str, List[str]],
        model_name: Optional[str] = None,
    ) -> Dict[str, Any]:

        req_data = self.make_llm_req_map(
            prompt=prompt,
            model_name=model_name,
        )
        resp = make_web_request(
            self.api_key,
            self.api_prefix + "batch_embeddings",
            "post",
            req_data,
        )
        return resp

    async def async_submit(
        self,
        prompt: Union[str, List[str]],
        model_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        req_data = self.make_llm_req_map(
            prompt=prompt,
            model_name=model_name,
        )
        async with aiohttp.ClientSession() as client:

            resp = await make_async_web_request(
                client,
                self.api_key,
                self.api_prefix + "batch_embeddings",
                "post",
                req_data,
            )
        return resp

    def check_result(
        self,
        id: str,
    ) -> Dict[str, Any]:
        """Check for the result of a batch request with the appropriate batch id."""
        resp = make_web_request(
            self.api_key,
            self.api_prefix + f"batch_embeddings/{id}/result",
            "get",
        )
        return resp

    async def async_check_result(
        self,
        id: str,
    ) -> Dict[str, Any]:
        """Check for the result of a batch request with the appropriate batch id."""
        async with aiohttp.ClientSession() as client:
            resp = await make_async_web_request(
                client,
                self.api_key,
                self.api_prefix + f"batch_embeddings/{id}/result",
                "get",
            )
        return resp

    def make_llm_req_map(
        self,
        model_name: Optional[str],
        prompt: Union[str, List[str]],
    ) -> Dict[str, Any]:

        req_data = {}
        if model_name is not None:
            req_data["model_name"] = model_name
        req_data["prompt"] = prompt
        return req_data
