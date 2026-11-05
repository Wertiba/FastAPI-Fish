import uvicorn

from app.infra.config import RunConfig
from app.main import app

if __name__ == "__main__":
    # Access lines come from ObservabilityMiddleware (with trace id), so uvicorn's own are off.
    config = app.state.dishka_container.get_sync(RunConfig)
    uvicorn.run(app, host=config.host, port=config.port, access_log=False, log_config=None)
