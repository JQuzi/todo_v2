from .start import router as start_router
from .settings import router as settings_router
from .new_task import router as new_task_router
from .matrix import router as matrix_router
from .quick_tasks import router as quick_tasks_router
from .archive import router as archive_router
from .task_actions import router as task_actions_router
from .today import router as today_router
from .search import router as search_router
from .bulk_delete import router as bulk_delete_router
from .admin import router as admin_router

routers = [
    start_router,
    settings_router,
    new_task_router,
    matrix_router,
    quick_tasks_router,
    archive_router,
    task_actions_router,
    today_router,
    search_router,
    bulk_delete_router,
    admin_router,
]
