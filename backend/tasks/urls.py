from django.urls import path

from .views import (
    AdminProjectDetailView,
    AdminProjectListCreateView,
    AdminTaskDetailView,
    AdminTaskListCreateView,
    EmployeeProjectListView,
    TaskDetailView,
    TaskListView,
)

urlpatterns = [
    path("tasks/", TaskListView.as_view(), name="task-list-create"),
    path("tasks/<int:pk>/", TaskDetailView.as_view(), name="task-detail"),
    path("my-projects/", EmployeeProjectListView.as_view(), name="employee-project-list"),
    path("admin/projects/", AdminProjectListCreateView.as_view(), name="admin-project-list"),
    path("admin/projects/<int:pk>/", AdminProjectDetailView.as_view(), name="admin-project-detail"),
    path("admin/tasks/", AdminTaskListCreateView.as_view(), name="admin-task-list"),
    path("admin/tasks/<int:pk>/", AdminTaskDetailView.as_view(), name="admin-task-detail"),
]