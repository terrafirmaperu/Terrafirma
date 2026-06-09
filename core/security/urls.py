from django.urls import path
from .views.dashboard.views import *
from .views.dniapi.views import *
from .views.moduletype.views import *
from .views.module.views import *
from .views.group.views import *
from .views.accessusers.views import *
from .views.databasebackups.views import *
from .views.supervisor_delete import (
    VerifySupervisorDeleteView,
    VerifySupervisorPredioUnlockView,
)

urlpatterns = [
    path('verify-supervisor-delete/', VerifySupervisorDeleteView.as_view(), name='verify_supervisor_delete'),
    path(
        'verify-supervisor-predio-unlock/',
        VerifySupervisorPredioUnlockView.as_view(),
        name='verify_supervisor_predio_unlock',
    ),
    # module_type
    path('module/type/', TypeListView.as_view(), name='moduletype_list'),
    path('module/type/add/', TypeCreateView.as_view(), name='moduletype_create'),
    path('module/type/update/<int:pk>/', TypeUpdateView.as_view(), name='moduletype_update'),
    path('module/type/delete/<int:pk>/', TypeDeleteView.as_view(), name='moduletype_delete'),
    # module
    path('module/', ModuleListView.as_view(), name='module_list'),
    path('module/add/', ModuleCreateView.as_view(), name='module_create'),
    path('module/update/<int:pk>/', ModuleUpdateView.as_view(), name='module_update'),
    path('module/delete/<int:pk>/', ModuleDeleteView.as_view(), name='module_delete'),
    # group
    path('group/', GroupListView.as_view(), name='group_list'),
    path('group/add/', GroupCreateView.as_view(), name='group_create'),
    path('group/update/<int:pk>/', GroupUpdateView.as_view(), name='group_update'),
    path('group/delete/<int:pk>/', GroupDeleteView.as_view(), name='group_delete'),
    # access
    path('access/users/', AccessUsersListView.as_view(), name='accessusers_list'),
    path('access/users/delete/<int:pk>/', AccessUsersDeleteView.as_view(), name='accessusers_delete'),
    # database
    path('database/backups/', DatabaseBackupsListView.as_view(), name='databasebackups_list'),
    path('database/backups/add/', DatabaseBackupsCreateView.as_view(), name='databasebackups_create'),
    path('database/backups/delete/<int:pk>/', DatabaseBackupsDeleteView.as_view(), name='databasebackups_delete'),
    # dashboard
    path('dashboard/update/', DashboardUpdateView.as_view(), name='dashboard_update'),
    # api dni
    path('api/dni/update/', DniApiConfigurationUpdateView.as_view(), name='dniapi_update'),
]
