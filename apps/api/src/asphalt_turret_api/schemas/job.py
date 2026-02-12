from pydantic import BaseModel

class JobStatusResponse(BaseModel):
    job_id: int
    type: str
    state: str
    progress: int
    total: int | None
    completed: int | None
    failed: int | None
    message: str | None
    created_at: str
    updated_at: str
