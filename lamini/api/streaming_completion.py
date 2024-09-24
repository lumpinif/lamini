import asyncio
import time
from typing import List, Optional, Union, Dict, Any

import aiohttp
import lamini
from lamini.api.lamini_config import get_config, get_configured_key, get_configured_url
from lamini.api.rest_requests import make_async_web_request, make_web_request


class StreamingCompletionObject:
    """Handler for streaming API endpoint on the Lamini Platform

    Parameters
    ----------
    request_params: Dict[str, Any]
        Parameters to pass into the request

    api_key: Optional[str]
        Lamini platform API key, if not provided the key stored
        within ~.lamini/configure.yaml will be used. If either
        don't exist then an error is raised.

    api_url: Optional[str]
        Lamini platform api url, only needed if a different url is needed outside of the
        defined ones here: https://github.com/lamini-ai/lamini-platform/blob/main/sdk/lamini/api/lamini_config.py#L68
            i.e. localhost, staging.lamini.ai, or api.lamini.ai
            Additionally, LLAMA_ENVIRONMENT can be set as an environment variable
            that will be grabbed for the url before any of the above defaults

    polling_interval: int
        Interval to wait before polling again

    max_errors: int = 0
        Number of errors before raising an exception
    """

    def __init__(
        self,
        request_params: Dict[str, Any],
        api_url: str,
        api_key: str,
        polling_interval: int,
        max_errors: int = 0,
    ):
        self.request_params = request_params
        self.api_url = api_url
        self.api_key = api_key
        self.done_streaming = False
        self.server = None
        self.polling_interval = polling_interval
        self.current_result = None
        self.error_count = 0
        self.max_errors = max_errors

    def __iter__(self) -> object:
        """Iteration definition

        Parameters
        ----------
        None

        Returns
        -------
        Reference to self
        """

        return self

    def __next__(self) -> str:
        """Iterator next step definition

        Parameters
        ----------
        None

        Returns
        -------
        str
            Streamed next result
        """

        return self.next()

    def next(self) -> str:
        """Retrieve the next iteration of the response stream

        Parameters
        ----------
        None

        Returns
        -------
        self.current_result: str
            Streamed result from the web request
        """

        if self.done_streaming:
            raise StopIteration()
        time.sleep(self.polling_interval)
        if self.server is not None:
            self.request_params["server"] = self.server
        try:
            resp = make_web_request(
                self.api_key,
                self.api_url,
                "post",
                self.request_params,
            )

            self.server = resp["server"]
            if resp["status"][0]:
                self.done_streaming = True
            self.current_result = resp["data"][0]
        except Exception as e:
            self.error_count += 1
            if self.error_count > self.max_errors:
                raise e
        return self.current_result


class AsyncStreamingCompletionObject:
    """Handler for asynchronous streaming API endpoint on the Lamini Platform

    Parameters
    ----------
    request_params: Dict[str, Any]
        Parameters to pass into the request

    api_key: Optional[str]
        Lamini platform API key, if not provided the key stored
        within ~.lamini/configure.yaml will be used. If either
        don't exist then an error is raised.

    api_url: Optional[str]
        Lamini platform api url, only needed if a different url is needed outside of the
        defined ones here: https://github.com/lamini-ai/lamini-platform/blob/main/sdk/lamini/api/lamini_config.py#L68
            i.e. localhost, staging.lamini.ai, or api.lamini.ai
            Additionally, LLAMA_ENVIRONMENT can be set as an environment variable
            that will be grabbed for the url before any of the above defaults

    polling_interval: int
        Interval to wait before polling again

    max_errors: int = 5
        Number of errors before raising an exception
    """

    def __init__(
        self,
        request_params: Dict[str, Any],
        api_url: str,
        api_key: str,
        polling_interval: int,
        max_errors: int = 5,
    ):
        self.request_params = request_params
        self.api_url = api_url
        self.api_key = api_key
        self.done_streaming = False
        self.server = None
        self.polling_interval = polling_interval
        self.current_result = None
        self.error_count = 0
        self.max_errors = max_errors

    def __aiter__(self) -> object:
        """Asychronous iteration definition

        Parameters
        ----------
        None

        Returns
        -------
        Reference to this instance of AsyncStreamingCompletionObject
        """

        return self

    async def __anext__(self):
        """Asynchronous next definition

        Parameters
        ----------
        None

        Returns
        -------
        str
            Current streaming result from the web request
        """

        return await self.next()

    async def next(self):
        """Retrieve the next iteration of the response stream

        Parameters
        ----------
        None

        Returns
        -------
        self.current_result: str
            Streamed result from the web request
        """

        if self.done_streaming:
            raise StopAsyncIteration()
        await asyncio.sleep(self.polling_interval)
        if self.server is not None:
            self.request_params["server"] = self.server
        try:
            async with aiohttp.ClientSession() as client:
                resp = await make_async_web_request(
                    client,
                    self.api_key,
                    self.api_url,
                    "post",
                    self.request_params,
                )
            self.server = resp["server"]
            if resp["status"][0]:
                self.done_streaming = True
            self.current_result = resp["data"][0]
        except Exception as e:
            self.error_count += 1
            if self.error_count > self.max_errors:
                raise e
        return self.current_result


class StreamingCompletion:
    """Handler for streaming completions API endpoint on the Lamini Platform

    Parameters
    ----------
    api_key: Optional[str]
        Lamini platform API key, if not provided the key stored
        within ~.lamini/configure.yaml will be used. If either
        don't exist then an error is raised.

    api_url: Optional[str]
        Lamini platform api url, only needed if a different url is needed outside of the
        defined ones here: https://github.com/lamini-ai/lamini-platform/blob/main/sdk/lamini/api/lamini_config.py#L68
            i.e. localhost, staging.lamini.ai, or api.lamini.ai
            Additionally, LLAMA_ENVIRONMENT can be set as an environment variable
            that will be grabbed for the url before any of the above defaults
    """

    def __init__(
        self,
        api_key: str = None,
        api_url: str = None,
    ):
        self.config = get_config()
        self.api_key = api_key or lamini.api_key or get_configured_key(self.config)
        self.api_url = api_url or lamini.api_url or get_configured_url(self.config)
        self.api_prefix = self.api_url + "/v1/"
        self.streaming_completions_url = self.api_prefix + "streaming_completions"

    def submit(
        self,
        prompt: Union[str, List[str]],
        model_name: Optional[str] = None,
        output_type: Optional[dict] = None,
        max_tokens: Optional[int] = None,
        max_new_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Conduct a web request to the streaming completions api endpoint with the
        provided prompt to the model_name if provided. Output_type handles the formatting
        of the output into a structure from this provided output_type.
        max_tokens and max_new_tokens are related to the total amount of tokens
        the model can use and generate. max_new_tokens is recommended to be used
        over max_tokens to adjust model output.

        Parameters
        ----------
        prompt: Union[str, List[str]]
            Prompt to send to LLM

        model_name: Optional[str] = None
            Which model to use from hugging face

        output_type: Optional[dict] = None
            Structured output format

        max_tokens: Optional[int] = None
            Max number of tokens for the model's generation

        max_new_tokens: Optional[int] = None
            Max number of new tokens from the model's generation

        Returns
        -------
        Dict[str, Any]
            Returned response from the web request
        """

        req_data = self.make_llm_req_map(
            prompt=prompt,
            model_name=model_name,
            output_type=output_type,
            max_tokens=max_tokens,
            max_new_tokens=max_new_tokens,
            server=None,
        )
        resp = make_web_request(
            self.api_key, self.streaming_completions_url, "post", req_data
        )
        return {
            "url": self.streaming_completions_url,
            "params": {**req_data, "server": resp["server"]},
        }

    async def async_submit(
        self,
        prompt: Union[str, List[str]],
        model_name: Optional[str] = None,
        output_type: Optional[dict] = None,
        max_tokens: Optional[int] = None,
        max_new_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Asynchronously send a web request to the streaming completions api endpoint with the
        provided prompt to the model_name if provided. Output_type handles the formatting
        of the output into a structure from this provided output_type.
        max_tokens and max_new_tokens are related to the total amount of tokens
        the model can use and generate. max_new_tokens is recommended to be used
        over max_tokens to adjust model output.

        Parameters
        ----------
        prompt: Union[str, List[str]]
            Prompt to send to LLM

        model_name: Optional[str] = None
            Which model to use from hugging face

        output_type: Optional[dict] = None
            Structured output format

        max_tokens: Optional[int] = None
            Max number of tokens for the model's generation

        max_new_tokens: Optional[int] = None
            Max number of new tokens from the model's generation

        Returns
        -------
        Dict[str, Any]
            Returned response from the web request
        """

        req_data = self.make_llm_req_map(
            prompt=prompt,
            model_name=model_name,
            output_type=output_type,
            max_tokens=max_tokens,
            max_new_tokens=max_new_tokens,
            server=None,
        )
        async with aiohttp.ClientSession() as client:
            resp = await make_async_web_request(
                client, self.api_key, self.streaming_completions_url, "post", req_data
            )
        return {
            "url": self.streaming_completions_url,
            "params": {**req_data, "server": resp["server"]},
        }

    def create(
        self,
        prompt: Union[str, List[str]],
        model_name: Optional[str] = None,
        output_type: Optional[dict] = None,
        max_tokens: Optional[int] = None,
        max_new_tokens: Optional[int] = None,
        polling_interval: Optional[float] = 1,
    ) -> object:
        """Instantiate a new StreamingCompletionObject

        Parameters
        ----------
        prompt: Union[str, List[str]]
            Prompt to send to LLM

        model_name: Optional[str] = None
            Which model to use from hugging face

        output_type: Optional[dict] = None
            Structured output format

        max_tokens: Optional[int] = None
            Max number of tokens for the model's generation

        max_new_tokens: Optional[int] = None
            Max number of new tokens from the model's generation

        polling_interval: Optional[float] = 1
            Interval to wait before polling again

        Returns
        -------
        StreamingCompletionObject
            Newly instantiated object
        """

        self.done_streaming = False
        self.server = None
        self.prompt = prompt
        self.model_name = model_name
        self.output_type = output_type
        self.max_tokens = max_tokens
        self.max_new_tokens = max_new_tokens
        req_data = self.make_llm_req_map(
            prompt=prompt,
            model_name=model_name,
            output_type=output_type,
            max_tokens=max_tokens,
            max_new_tokens=max_new_tokens,
            server=None,
        )
        return StreamingCompletionObject(
            req_data,
            api_key=self.api_key,
            api_url=self.streaming_completions_url,
            polling_interval=polling_interval,
        )

    def async_create(
        self,
        prompt: Union[str, List[str]],
        model_name: Optional[str] = None,
        output_type: Optional[dict] = None,
        max_tokens: Optional[int] = None,
        max_new_tokens: Optional[int] = None,
        polling_interval: Optional[float] = 1,
    ) -> object:
        """Instantiate a new AsyncStreamingCompletionObject

        Parameters
        ----------
        prompt: Union[str, List[str]]
            Prompt to send to LLM

        model_name: Optional[str] = None
            Which model to use from hugging face

        output_type: Optional[dict] = None
            Structured output format

        max_tokens: Optional[int] = None
            Max number of tokens for the model's generation

        max_new_tokens: Optional[int] = None
            Max number of new tokens from the model's generation

        polling_interval: Optional[float] = 1
            Interval to wait before polling again

        Returns
        -------
        AsyncStreamingCompletionObject
            Newly instantiated object
        """

        self.done_streaming = False
        self.server = None
        self.prompt = prompt
        self.model_name = model_name
        self.output_type = output_type
        self.max_tokens = max_tokens
        self.max_new_tokens = max_new_tokens
        req_data = self.make_llm_req_map(
            prompt=prompt,
            model_name=model_name,
            output_type=output_type,
            max_tokens=max_tokens,
            max_new_tokens=max_new_tokens,
            server=None,
        )
        return AsyncStreamingCompletionObject(
            req_data,
            api_key=self.api_key,
            api_url=self.streaming_completions_url,
            polling_interval=polling_interval,
        )

    def make_llm_req_map(
        self,
        model_name: Optional[str],
        prompt: Union[str, List[str]],
        output_type: Optional[dict],
        max_tokens: Optional[int],
        max_new_tokens: Optional[int],
        server: Optional[str],
    ) -> Dict[str, Any]:
        """Make a web request to the Lamini Platform

        Parameters
        ----------
        model_name: Optional[str]
            Which model to use from hugging face

        prompt: Union[str, List[str]]
            Prompt to send to LLM

        output_type: Optional[dict] = None
            Structured output format

        max_tokens: Optional[int] = None
            Max number of tokens for the model's generation

        max_new_tokens: Optional[int] = None
            Max number of new tokens from the model's generation

        server: Optional[str]
            Which Lamini Platform to make the request out to

        Returns
        -------
        req_data: Dict[str, Any]
            Response from the web request
        """

        req_data = {}
        req_data["model_name"] = model_name
        req_data["prompt"] = prompt
        req_data["output_type"] = output_type
        req_data["max_tokens"] = max_tokens
        if max_new_tokens is not None:
            req_data["max_new_tokens"] = max_new_tokens
        if server is not None:
            req_data["server"] = server
        return req_data
