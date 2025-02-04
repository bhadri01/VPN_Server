import asyncio
from contextlib import asynccontextmanager
from datetime import datetime

import uvicorn
from fastapi import Depends, FastAPI
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import (DataError, IntegrityError, InterfaceError,
                            OperationalError, ProgrammingError,
                            SQLAlchemyError)
from starlette.exceptions import HTTPException as StarletteHTTPException

# route import
from app.core.config import settings
from app.core.database import Base, get_session, master_db_engine
from app.logs.logging import logger
# import expection handlers
from app.utils.exception_handler import (authentication_error_handler,
                                         data_error_handler,
                                         database_exception_handler,
                                         global_exception_handler,
                                         http_exception_handler,
                                         integrity_error_handler,
                                         interface_error_handler,
                                         operational_error_handler,
                                         permission_error_handler,
                                         programming_error_handler,
                                         timeout_error_handler,
                                         type_error_handler,
                                         validation_exception_handler,
                                         value_error_handler)

from app.utils.httpbearer import get_current_user
from app.utils.token_blacklist import cleanup_expired_tokens

# Determine if running in production
ENV = settings.environment

# Disable documentation if in production
if ENV == "production":
    app = FastAPI(docs_url=None, redoc_url=None)
else:
    app = FastAPI(title=settings.app_name, version="0.1.0",
                  swagger_ui_parameters={"persistAuthorization": True})

origins = [
    "*"
]

# Include exception handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(SQLAlchemyError, database_exception_handler)
app.add_exception_handler(IntegrityError, integrity_error_handler)
app.add_exception_handler(DataError, data_error_handler)
app.add_exception_handler(OperationalError, operational_error_handler)
app.add_exception_handler(ProgrammingError, programming_error_handler)
app.add_exception_handler(InterfaceError, interface_error_handler)
app.add_exception_handler(asyncio.TimeoutError, timeout_error_handler)
app.add_exception_handler(PermissionError, permission_error_handler)
app.add_exception_handler(HTTPException, authentication_error_handler)
app.add_exception_handler(ValueError, value_error_handler)
app.add_exception_handler(TypeError, type_error_handler)
app.add_exception_handler(Exception, global_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allows all headers
)

from app.api.users.routers import router as user_router


async def start_periodic_cleanup():
    while True:
        await asyncio.sleep(60)
        try:
            logger.info(
                f'[*] FastAPI startup: Cleaning expired Tokens {datetime.now()}')
            cleanup_expired_tokens()
        except Exception as e:
            logger.error(f'Error during token cleanup: {e}')


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with master_db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info('[*] FastAPI startup: Database connected')

    loop = asyncio.get_event_loop()
    loop.create_task(start_periodic_cleanup())
    logger.info('[*] FastAPI startup: Token thread started')

    yield

    loop.stop()
    logger.info('[*] FastAPI shutdown: Token thread stopping')
    logger.info('[*] FastAPI shutdown: Database disconnected')


app.router.lifespan_context = lifespan


app.include_router(user_router, tags=["Users"], prefix="/api/users")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, reload_excludes=["logs/*"])