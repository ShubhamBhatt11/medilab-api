"""Dev entrypoint: python -m app

On Windows, psycopg's async mode requires a selector event loop, but the
default (and uvicorn's) loop is the Proactor loop. Passing an explicit
loop_factory to asyncio.run is the supported fix on Python 3.12+.
In Docker/Linux the plain `uvicorn app.main:app` CLI works as usual.
"""
import asyncio
import selectors
import sys

import uvicorn

config = uvicorn.Config("app.main:app", host="127.0.0.1", port=8000)
server = uvicorn.Server(config)

if sys.platform == "win32":
    asyncio.run(
        server.serve(),
        loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()),
    )
else:
    asyncio.run(server.serve())
