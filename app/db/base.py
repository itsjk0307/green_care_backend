from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Register all ORM models with metadata (Alembic, mappers). Use submodule imports
# to avoid circular imports (model modules import Base from this file).
import app.models.ai_result  # noqa: E402, F401
import app.models.detection_report  # noqa: E402, F401
import app.models.golf_course  # noqa: E402, F401
import app.models.report  # noqa: E402, F401
import app.models.user  # noqa: E402, F401
import app.models.work_area  # noqa: E402, F401
import app.models.work_report  # noqa: E402, F401
import app.models.daily_work_plan  # noqa: E402, F401
