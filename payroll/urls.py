from django.urls import path
from . import views

urlpatterns = [
    # Authorization Modules
    path('', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Platform Dashboard Gateways
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/staff/', views.staff_dashboard, name='staff_dashboard'),

    # Workforce Control Infrastructure
    path('dashboard/admin/employees/', views.manage_employees, name='manage_employees'),
    path('dashboard/admin/attendance/', views.attendance_tracker, name='attendance_tracker'),

    # Absence Requests Management
    path('dashboard/leaves/', views.leave_manager, name='leave_manager'),
    path('dashboard/leaves/approve/<int:leave_id>/', views.approve_leave, name='approve_leave'),
    path('dashboard/leaves/reject/<int:leave_id>/', views.reject_leave, name='reject_leave'),

    # Core Financial Operations
    path('dashboard/admin/computation/', views.payroll_computation, name='payroll_computation'),
    path('dashboard/admin/payslips/', views.admin_payslips, name='admin_payslips'),
    path('dashboard/admin/reports/', views.admin_reports, name='admin_reports'),
    path('dashboard/payslip/<int:payroll_id>/', views.view_payslip, name='view_payslip'),
]