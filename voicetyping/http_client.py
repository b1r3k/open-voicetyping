import httpx

from httpx import HTTPStatusError

from .logging import root_logger

logger = root_logger.getChild(__name__)


class RetryException(RuntimeError):
    pass


class HTTPClientError(httpx.HTTPStatusError):
    service = "generic"

    @classmethod
    def from_httpx_exception(cls, exc: httpx.HTTPStatusError, msg=None):
        msg = msg or exc.args[0]
        return cls(msg, request=exc.request, response=exc.response)

    @property
    def status_code(self):
        return self.response.status_code

    @property
    def response_summary(self) -> str:
        content = self.response.content
        status_code = self.status_code
        msg = f"[{self.service}] Status code: {status_code} response content: {content}"
        return msg

    @property
    def request_summary(self) -> str:
        self.request.read()
        request = (
            f"[{self.service}] {self.request.method} {self.request.url} {self.request.headers}"
            f" {self.request.content[:1024]}"
        )
        return request


class AsyncHttpClient:
    def __init__(
        self,
        max_keepalive_connections=100,
        max_connections=1000,
        connect_timeout: int = 5,
        follow_redirects: bool = True,
        verify_ssl: bool = True,
        exception_class=HTTPClientError,
    ):
        self._limits = httpx.Limits(
            max_keepalive_connections=max_keepalive_connections, max_connections=max_connections
        )
        self._timeout = httpx.Timeout(None, connect=connect_timeout)
        self._base_exception = exception_class
        self._session = None
        self._httpx_opts = dict(
            limits=self._limits, timeout=self._timeout, follow_redirects=follow_redirects, verify=verify_ssl
        )

    @property
    def session(self):
        if self._session is None:
            self._session = httpx.AsyncClient(**self._httpx_opts)
        return self._session

    async def aclose(self):
        if self._session is not None:
            try:
                await self._session.aclose()
            except Exception:
                logger.debug("Failed to close session", exc_info=True)
            finally:
                self._session = None

    async def request(self, *args, **kwargs):
        retries = kwargs.pop("retries", 3)
        try:
            response = await self.session.request(*args, **kwargs)
            response.raise_for_status()
            return response
        except HTTPStatusError as exc:
            wrapped_exception = self._base_exception.from_httpx_exception(exc)
            try:
                request_summary = wrapped_exception.request_summary
                logger.debug("Failed request: %s", request_summary)
            except Exception:
                logger.exception("Error getting request summary")
            try:
                response_summary = wrapped_exception.response_summary
                logger.debug("Error response %s", response_summary)
            except Exception:
                logger.exception("Error getting response summary")
            raise wrapped_exception from exc
        except RuntimeError as ex:
            await self.aclose()
            retries -= 1
            if retries > 0:
                return await self.request(*args, **kwargs, retries=retries)
            raise RetryException("Failed to make request after retries") from ex

    async def get(self, url, *args, **kwargs):
        return await self.request("GET", url, *args, **kwargs)

    async def post(self, url, *args, **kwargs):
        return await self.request("POST", url, *args, **kwargs)

    async def put(self, url, *args, **kwargs):
        return await self.request("PUT", url, *args, **kwargs)

    async def delete(self, url, *args, **kwargs):
        return await self.request("DELETE", url, *args, **kwargs)

    async def patch(self, url, *args, **kwargs):
        return await self.request("PATCH", url, *args, **kwargs)

    async def head(self, url, *args, **kwargs):
        return await self.request("HEAD", url, *args, **kwargs)

    def build_request(self, *args, **kwargs):
        return self.session.build_request(*args, **kwargs)

    async def send(self, *args, **kwargs):
        return await self.session.send(*args, **kwargs)
