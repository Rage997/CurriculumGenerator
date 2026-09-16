"""Run the API directly: ``python -m curriculum_generator.api``.

Host/port come from the environment (HOST, PORT) so the same entrypoint works
in a container. For production, prefer a process manager or uvicorn directly.
"""

import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "curriculum_generator.api.app:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8000")),
    )
