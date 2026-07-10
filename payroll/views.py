from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django import forms
from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum
from django.utils import timezone
from datetime import datetime
import calendar
from .models import Profile, Employee, Payroll, Leave, Attendance, Payslip, AdminProfile


# --- 📋 REGISTER FORM CLASS ---
class CustomRegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True,
                                 widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=30, required=True,
                                widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(
        attrs={'class': 'form-control', 'placeholder': 'example@mail.com'}))
    contact_no = forms.CharField(max_length=20, required=False, widget=forms.TextInput(
        attrs={'class': 'form-control', 'placeholder': 'Contact Number'}))

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if len(username) < 6:
            raise forms.ValidationError("The username must be at least 6 characters long.")
        return username


# --- 🛡️ SECURITY AUTHS & GATEKEEPERS ---
def is_superadmin(user):
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.role == 'superadmin'


def is_management(user):
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.role in ['superadmin', 'admin',
                                                                                        'hr_manager', 'payroll_officer']


# --- 🔑 SESSIONS AND ACCOUNT ACCESS ---
def register_view(request):
    if request.method == 'POST':
        form = CustomRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.first_name = form.cleaned_data.get('first_name')
            user.last_name = form.cleaned_data.get('last_name')
            user.email = form.cleaned_data.get('email')
            user.save()

            user.profile.role = 'employee'
            user.profile.status = 'active'
            user.profile.contact_no = form.cleaned_data.get('contact_no')
            user.profile.save()

            Employee.objects.get_or_create(
                user=user,
                defaults={
                    'department': 'Operations',
                    'position': 'Junior Associate',
                    'salary': 0.00
                }
            )
            messages.success(request, "Registration successful! Proceed to Login.")
            return redirect('login')
        else:
            messages.error(request, "Registration failed. Please check form validation rules.")
    else:
        form = CustomRegisterForm()
    return render(request, 'payroll/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                if user.profile.role in ['superadmin', 'admin', 'hr_manager', 'payroll_officer']:
                    return redirect('admin_dashboard')
                return redirect('staff_dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'payroll/login.html', {'form': form})


# --- 📊 MASTER EXECUTIVE CONSOLE ---
@login_required
def admin_dashboard(request):
    if not is_management(request.user): return redirect('staff_dashboard')
    user_role = request.user.profile.role

    if user_role == 'superadmin':
        total_employees = Employee.objects.count()
        total_payroll = Payroll.objects.aggregate(total=Sum('net_salary'))['total'] or 0.00
    else:
        dept = getattr(request.user.admin_profile, 'managed_department', 'General Operations')
        total_employees = Employee.objects.filter(department=dept).count()
        total_payroll = Payroll.objects.filter(employee__department=dept).aggregate(total=Sum('net_salary'))[
                            'total'] or 0.00

    return render(request, 'payroll/admin_dashboard.html', {
        'total_employees': total_employees,
        'total_payroll_month': f"₱{total_payroll:,.2f}"
    })


# --- 👥 DIRECTORY MATRIX MANAGEMENT ---
@login_required
def manage_employees(request):
    if not is_management(request.user): return redirect('staff_dashboard')
    user_role = request.user.profile.role

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        new_role = request.POST.get('account_role')
        target_dept = request.POST.get('department', '').strip()
        target_pos = request.POST.get('position', '').strip()
        salary_input = request.POST.get('salary')

        try:
            target_user = User.objects.get(pk=user_id)

            if user_role != 'superadmin':
                admin_dept = request.user.admin_profile.managed_department
                if not hasattr(target_user,
                               'employee_profile') or target_user.employee_profile.department != admin_dept:
                    messages.error(request, "Access Denied: You cannot modify parameters outside your own department.")
                    return redirect('manage_employees')

                emp = target_user.employee_profile
                if target_pos: emp.position = target_pos
                if salary_input: emp.salary = salary_input
                emp.save()
                messages.success(request, f"Successfully updated records for {target_user.get_full_name()}.")

            else:
                if new_role == 'superadmin':
                    if Profile.objects.filter(role='superadmin').exclude(user=target_user).exists():
                        messages.error(request, "Operation Aborted: Only 1 Single Business Owner Superadmin can exist.")
                        return redirect('manage_employees')

                    target_user.profile.role = 'superadmin'
                    target_user.is_staff = True
                    target_user.save()
                    target_user.profile.save()
                    AdminProfile.objects.filter(user=target_user).delete()
                    Employee.objects.filter(user=target_user).delete()
                    messages.success(request, f"Global Ownership transferred safely to {target_user.get_full_name()}.")

                elif new_role in ['admin', 'hr_manager', 'payroll_officer']:
                    target_user.profile.role = new_role
                    target_user.is_staff = True
                    target_user.save()
                    target_user.profile.save()

                    admin_prof, _ = AdminProfile.objects.get_or_create(user=target_user)
                    admin_prof.managed_department = target_dept if target_dept else 'Operations'
                    admin_prof.save()
                    Employee.objects.filter(user=target_user).delete()
                    messages.success(request,
                                     f"{target_user.get_full_name()} assigned as Admin Head for {admin_prof.managed_department}.")

                else:
                    target_user.profile.role = 'employee'
                    target_user.is_staff = False
                    target_user.save()
                    target_user.profile.save()
                    AdminProfile.objects.filter(user=target_user).delete()

                    emp, _ = Employee.objects.get_or_create(user=target_user)
                    emp.department = target_dept or 'Operations'
                    emp.position = target_pos or 'Junior Associate'
                    if salary_input: emp.salary = salary_input
                    emp.save()
                    messages.success(request, f"Configured {target_user.get_full_name()} as regular employee.")

        except User.DoesNotExist:
            messages.error(request, "Target user record missing.")
        return redirect('manage_employees')

    if user_role == 'superadmin':
        all_users = User.objects.all().select_related('profile', 'employee_profile', 'admin_profile').order_by('id')
    else:
        admin_dept = request.user.admin_profile.managed_department
        all_users = User.objects.filter(employee_profile__department=admin_dept).select_related('profile',
                                                                                                'employee_profile').order_by(
            'id')

    return render(request, 'payroll/manage_employees.html', {'all_users': all_users})


# --- 🕒 SHIFTS TRACKER ---
@login_required
def attendance_tracker(request):
    if not is_management(request.user): return redirect('admin_dashboard')
    user_role = request.user.profile.role

    if request.method == 'POST':
        emp_id = request.POST.get('employee_id')
        work_date = request.POST.get('work_date')
        status = request.POST.get('attendance_status', 'Present')

        try:
            employee = Employee.objects.get(pk=emp_id)
            if user_role != 'superadmin' and employee.department != request.user.admin_profile.managed_department:
                messages.error(request, "Unauthorized operation.")
            else:
                Attendance.objects.create(employee=employee, work_date=work_date, hours_worked=8.0,
                                          attendance_status=status)
                messages.success(request, f"Attendance logged for {employee.user.get_full_name()}.")
        except Exception as e:
            messages.error(request, f"Failure to commit: {str(e)}")
        return redirect('attendance_tracker')

    if user_role == 'superadmin':
        employees = Employee.objects.all().select_related('user')
        attendance_records = Attendance.objects.all().select_related('employee__user').order_by('-work_date')[:15]
    else:
        dept = request.user.admin_profile.managed_department
        employees = Employee.objects.filter(department=dept).select_related('user')
        attendance_records = Attendance.objects.filter(employee__department=dept).select_related(
            'employee__user').order_by('-work_date')[:15]

    return render(request, 'payroll/attendance_tracker.html',
                  {'employees': employees, 'attendance_records': attendance_records})


# --- 🗓️ ABSENCE FLOW PORTER ---
@login_required
def leave_manager(request):
    if request.method == 'POST' and request.user.profile.role == 'employee':
        try:
            employee = request.user.employee_profile
            start_date = datetime.strptime(request.POST.get('start_date'), '%Y-%m-%d').date()
            end_date = datetime.strptime(request.POST.get('end_date'), '%Y-%m-%d').date()
            Leave.objects.create(
                employee=employee, leave_type=request.POST.get('leave_type'),
                start_date=start_date, end_date=end_date,
                total_days=(end_date - start_date).days + 1,
                reason=request.POST.get('reason'), status='Pending'
            )
            messages.success(request, "Absence request uploaded.")
        except Exception:
            messages.error(request, "Calculation mismatch error.")
        return redirect('leave_manager')

    user_role = request.user.profile.role
    if user_role == 'superadmin':
        leaves = Leave.objects.all().select_related('employee__user').order_by('-date_requested')
    elif user_role in ['admin', 'hr_manager', 'payroll_officer']:
        dept = request.user.admin_profile.managed_department
        leaves = Leave.objects.filter(employee__department=dept).select_related('employee__user').order_by(
            '-date_requested')
    else:
        leaves = Leave.objects.filter(employee=request.user.employee_profile).order_by('-date_requested')

    return render(request, 'payroll/leave_manager.html', {'leaves': leaves})


@login_required
def approve_leave(request, leave_id):
    if not is_management(request.user): return redirect('admin_dashboard')
    leave = get_object_or_404(Leave, pk=leave_id)
    if request.user.profile.role != 'superadmin' and leave.employee.department != request.user.admin_profile.managed_department:
        messages.error(request, "Unauthorized boundary shift.")
    else:
        leave.status = 'Approved'
        leave.save()
        messages.success(request, "Leave entry approved.")
    return redirect('leave_manager')


@login_required
def reject_leave(request, leave_id):
    if not is_management(request.user): return redirect('admin_dashboard')
    leave = get_object_or_404(Leave, pk=leave_id)
    if request.user.profile.role != 'superadmin' and leave.employee.department != request.user.admin_profile.managed_department:
        messages.error(request, "Unauthorized boundary shift.")
    else:
        leave.status = 'Rejected'
        leave.save()
        messages.warning(request, "Leave entry rejected.")
    return redirect('leave_manager')


# --- ₱ AUTOMATED SEMI-MONTHLY CALCULATION RUNS ---
@login_required
def payroll_computation(request):
    if not is_management(request.user): return redirect('admin_dashboard')
    user_role = request.user.profile.role

    if request.method == 'POST':
        emp_id = request.POST.get('employee_id')
        target_month_str = request.POST.get('target_month')
        payroll_cycle = request.POST.get('payroll_cycle')

        try:
            employee = Employee.objects.get(pk=emp_id)
            if user_role != 'superadmin' and employee.department != request.user.admin_profile.managed_department:
                messages.error(request, "Execution boundary protection block triggered.")
                return redirect('payroll_computation')

            year, month = map(int, target_month_str.split('-'))

            if payroll_cycle == 'first_half':
                start_date = datetime(year, month, 1).date()
                end_date = datetime(year, month, 15).date()
                cycle_label = "15th Day Cycle"
            else:
                start_date = datetime(year, month, 16).date()
                last_day = calendar.monthrange(year, month)[1]
                end_date = datetime(year, month, last_day).date()
                cycle_label = "End-of-Month Cycle"

            attendance_logs = Attendance.objects.filter(employee=employee, work_date__range=[start_date, end_date],
                                                        attendance_status='Present')
            total_hours = attendance_logs.aggregate(total=Sum('hours_worked'))['total'] or 0

            hourly_rate = float(employee.salary) / 160.0
            gross_salary = float(total_hours) * hourly_rate
            deductions = gross_salary * 0.12
            net_salary = gross_salary - deductions

            payroll = Payroll.objects.create(
                employee=employee, payroll_period_start=start_date, payroll_period_end=end_date,
                gross_salary=gross_salary, deductions=deductions, net_salary=net_salary, payroll_status='Completed'
            )
            Payslip.objects.create(payroll=payroll, issue_date=timezone.now().date(),
                                   remarks=f"Semi-Monthly Calculation [{cycle_label}]. Total Hours: {total_hours}. Rate: ₱{hourly_rate:.2f}/hr.")
            messages.success(request, f"Successfully compiled {cycle_label} for {employee.user.get_full_name()}!")
        except Exception as e:
            messages.error(request, f"Anomaly caught: {str(e)}")
        return redirect('payroll_computation')

    if user_role == 'superadmin':
        employees = Employee.objects.all().select_related('user')
        payrolls = Payroll.objects.all().select_related('employee__user').order_by('-payroll_id')
    else:
        dept = request.user.admin_profile.managed_department
        employees = Employee.objects.filter(department=dept).select_related('user')
        payrolls = Payroll.objects.filter(employee__department=dept).select_related('employee__user').order_by(
            '-payroll_id')

    return render(request, 'payroll/payroll_computation.html', {'employees': employees, 'payrolls': payrolls})


@login_required
def admin_payslips(request):
    if not is_management(request.user): return redirect('admin_dashboard')
    user_role = request.user.profile.role
    if user_role == 'superadmin':
        payrolls = Payroll.objects.all().select_related('employee__user').order_by('-payroll_id')
    else:
        dept = request.user.admin_profile.managed_department
        payrolls = Payroll.objects.filter(employee__department=dept).select_related('employee__user').order_by(
            '-payroll_id')
    return render(request, 'payroll/admin_payslips.html', {'payrolls': payrolls})


# --- 📉 SYSTEM CORPORATE AUDIT REPORTS ---
@login_required
def admin_reports(request):
    if not is_superadmin(request.user):
        messages.error(request, "Access Denied: Operational audits are restricted to the Business Owner.")
        return redirect('admin_dashboard')

    total_spend = Payroll.objects.aggregate(total=Sum('net_salary'))['total'] or 0.00
    total_gross = Payroll.objects.aggregate(total=Sum('gross_salary'))['total'] or 0.00
    total_deductions = Payroll.objects.aggregate(total=Sum('deductions'))['total'] or 0.00

    total_personnel = Employee.objects.count()
    active_leaves_count = Leave.objects.filter(status='Approved').count()
    pending_leaves_count = Leave.objects.filter(status='Pending').count()

    departmental_costs = Employee.objects.values('department').annotate(
        total_allocated=Sum('salary'),
        staff_count=models.Count('employee_id')
    ).order_by('-total_allocated')

    historical_runs = Payroll.objects.select_related('employee__user').order_by('-payroll_id')[:10]

    context = {
        'total_spend': f"₱{total_spend:,.2f}",
        'total_gross': f"₱{total_gross:,.2f}",
        'total_deductions': f"₱{total_deductions:,.2f}",
        'total_personnel': total_personnel,
        'active_leaves': active_leaves_count,
        'pending_leaves': pending_leaves_count,
        'departments': departmental_costs,
        'historical_runs': historical_runs,
    }
    return render(request, 'payroll/admin_reports.html', context)


@login_required
def view_payslip(request, payroll_id):
    try:
        payroll = Payroll.objects.select_related('employee__user', 'payslip').get(pk=payroll_id)
        if request.user.profile.role == 'employee' and payroll.employee != request.user.employee_profile:
            return redirect('staff_dashboard')
        return render(request, 'payroll/view_payslip.html',
                      {'payroll': payroll, 'clean_remarks': payroll.payslip.remarks or ""})
    except Payroll.DoesNotExist:
        return redirect('admin_dashboard')


# --- 👥 EMPLOYEE ACCESS DESK ---
@login_required
def staff_dashboard(request):
    if is_management(request.user): return redirect('admin_dashboard')
    try:
        employee = request.user.employee_profile
    except Employee.DoesNotExist:
        return redirect('logout')

    if request.method == 'POST' and 'clock_in' in request.POST:
        work_date = request.POST.get('work_date')
        if not Attendance.objects.filter(employee=employee, work_date=work_date).exists():
            Attendance.objects.create(employee=employee, work_date=work_date, hours_worked=8.0,
                                      attendance_status='Present')
            messages.success(request, "Shift logged successfully.")
        return redirect('staff_dashboard')

    my_payrolls = Payroll.objects.filter(employee=employee).order_by('-payroll_id')
    my_attendance = Attendance.objects.filter(employee=employee).order_by('-work_date')[:10]
    return render(request, 'payroll/staff_dashboard.html', {'my_payrolls': my_payrolls, 'my_attendance': my_attendance})


def logout_view(request):
    logout(request);
    return redirect('login')