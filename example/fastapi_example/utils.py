from contextlib import contextmanager
from typing import Iterator

from fastapi import FastAPI
from pait.app.starlette import Pait
from pait.exceptions import PaitBaseException, PaitBaseParamException, TipException
from pait.model.status import PaitStatus
from pydantic import ValidationError
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response

global_pait: Pait = Pait(author=("so1n",), status=PaitStatus.test)


def api_exception(request: Request, exc: Exception) -> Response:
    if isinstance(exc, TipException):
        exc = exc.exc
    if isinstance(exc, PaitBaseParamException):
        return JSONResponse({"code": -1, "msg": f"error param:{exc.param}, {exc.msg}"})
    elif isinstance(exc, PaitBaseException):
        return JSONResponse({"code": -1, "msg": str(exc)})
    elif isinstance(exc, ValidationError):
        error_param_list: list = []
        for i in exc.errors():
            error_param_list.extend(i["loc"])
        return JSONResponse({"code": -1, "msg": f"miss param: {error_param_list}"})
    elif isinstance(exc, HTTPException):
        return HTMLResponse(status_code=exc.status_code, content=str(exc), headers=getattr(exc, "headers", {}))
    return JSONResponse({"code": -1, "msg": str(exc)})


@contextmanager
def create_app() -> Iterator[FastAPI]:
    import uvicorn
    from pait.extra.config import apply_block_http_method_set
    from pait.g import config
    from pait.openapi.doc_route import add_doc_route

    config.init_config(apply_func_list=[apply_block_http_method_set({"HEAD", "OPTIONS"})])

    app: FastAPI = FastAPI()
    yield app
    app.add_exception_handler(PaitBaseException, api_exception)
    app.add_exception_handler(ValidationError, api_exception)
    app.add_exception_handler(RuntimeError, api_exception)

    add_doc_route(prefix="/api-doc", title="Grpc Api Doc", app=app)
    uvicorn.run(app)
