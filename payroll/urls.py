from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Admin Workspace View Routings
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/admin/employees/', views.manage_employees, name='manage_employees'),
    path('dashboard/admin/computation/', views.payroll_computation, name='payroll_computation'),
    path('dashboard/admin/payslips/', views.admin_payslips, name='admin_payslips'),
    path('dashboard/admin/reports/', views.admin_reports, name='admin_reports'),
    path('dashboard/leaves/', views.leave_manager, name='leave_manager'),
    # Employee Workspace View Routings
    path('dashboard/staff/', views.staff_dashboard, name='staff_dashboard'),
]