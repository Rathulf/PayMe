from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django import forms
from django.contrib.auth.models import User
from django.db.models import Sum
from django.utils import timezone
from datetime import datetime
from .models import Profile, Employee, Payroll, Leave, Attendance, Payslip, AdminProfile


# --- 📋 REGISTRATION FORM DEFINITION ---
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


# --- 🛡️ ACCESS GATEKEEPER PERMISSIONS ---
def is_admin_user(user):
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.role == 'admin'


# --- 🔑 AUTHENTICATION AND SIGNUP VIEWS ---
def register_view(request):
    if request.method == 'POST':
        form = CustomRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.first_name = form.cleaned_data.get('first_name')
            user.last_name = form.cleaned_data.get('last_name')
            user.email = form.cleaned_data.get('email')

            user.profile.role = 'employee'
            user.profile.status = 'inactive'
            user.profile.contact_no = form.cleaned_data.get('contact_no')
            user.save()

            Employee.objects.get_or_create(
                user=user,
                defaults={
                    'department': 'Pending Assignment',
                    'position': 'Unassigned Staff',
                    'salary': 0.00,
                    'date_hired': user.date_joined.date()
                }
            )

            messages.success(request, "Registration successful! Your account is pending administrator configuration.")
            return redirect('login')
        else:
            messages.error(request, "Registration failed. Please correct the form validation errors.")
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
                if user.profile.role == 'admin':
                    return redirect('admin_dashboard')
                else:
                    return redirect('staff_dashboard')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, 'payroll/login.html', {'form': form})


# --- 📊 ADMINISTRATIVE HUB PANELS ---
@login_required
def admin_dashboard(request):
    if not is_admin_user(request.user):
        return redirect('staff_dashboard')

    total_employees_count = Employee.objects.count()
    today_date = timezone.now().date()
    today_present_count = Attendance.objects.filter(work_date=today_date, attendance_status='Present').count()

    if total_employees_count > 0:
        total_payroll_calc = Payroll.objects.aggregate(total_sum=Sum('net_salary'))['total_sum'] or 0.00
        pending_payslips_count = Payroll.objects.filter(payroll_status='Pending').count()
        recent_activities_list = Payroll.objects.all().order_by('-payroll_id')[:5]
    else:
        total_payroll_calc = 0.00
        pending_payslips_count = 0
        recent_activities_list = []

    context = {
        'total_employees': total_employees_count,
        'today_present': today_present_count,
        'total_payroll_month': f"{total_payroll_calc:,.2f}",
        'pending_payslips': pending_payslips_count,
        'recent_activities': recent_activities_list,
    }
    return render(request, 'payroll/admin_dashboard.html', context)


@login_required
def manage_employees(request):
    if not is_admin_user(request.user):
        return redirect('staff_dashboard')

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        new_role = request.POST.get('account_role')
        selected_type = request.POST.get('admin_type', 'hr_manager')

        try:
            user_account = User.objects.get(pk=user_id)

            if new_role == 'admin':
                user_account.profile.role = 'admin'
                user_account.profile.status = 'active'
                user_account.is_staff = True
                user_account.save()
                user_account.profile.save()

                admin_row, created = AdminProfile.objects.get_or_create(user=user_account)
                admin_row.admin_type = selected_type

                if selected_type == 'business_owner':
                    admin_row.managed_department = 'Global Executive Oversight'
                elif selected_type == 'it_admin':
                    admin_row.managed_department = 'IT Infrastructure & Security'
                else:
                    admin_row.managed_department = request.POST.get('department', 'Human Resources')

                admin_row.save()
                Employee.objects.filter(user=user_account).delete()
                messages.success(request, f"Successfully assigned Admin settings for {user_account.get_full_name()}!")

            else:
                user_account.profile.role = 'employee'
                user_account.is_staff = False
                user_account.save()
                user_account.profile.save()

                AdminProfile.objects.filter(user=user_account).delete()

                employee, created = Employee.objects.get_or_create(
                    user=user_account,
                    defaults={'salary': 0.00, 'date_hired': user_account.date_joined.date()}
                )
                employee.department = request.POST.get('department', 'General')
                employee.position = request.POST.get('position', 'Staff')
                employee.salary = request.POST.get('salary', 0.00) or 0.00
                employee.date_hired = request.POST.get('date_hired')
                employee.save()

                messages.success(request,
                                 f"Successfully reverted {user_account.get_full_name()} to employee data grid.")

        except User.DoesNotExist:
            messages.error(request, "Target user record could not be located.")

        return redirect('manage_employees')

    regular_employees = Employee.objects.all().select_related('user').order_by('employee_id')
    admin_personnel = AdminProfile.objects.all().select_related('user').order_by('admin_id')

    return render(request, 'payroll/manage_employees.html', {
        'regular_employees': regular_employees,
        'admin_personnel': admin_personnel
    })


# --- 🕒 SYSTEM OPERATION MODULES ---
@login_required
def attendance_tracker(request):
    if not is_admin_user(request.user):
        return redirect('staff_dashboard')

    if request.method == 'POST':
        emp_id = request.POST.get('employee_id')
        work_date = request.POST.get('work_date')
        hours_worked = request.POST.get('hours_worked', 8.0)
        status = request.POST.get('attendance_status', 'Present')

        try:
            employee = Employee.objects.get(pk=emp_id)
            Attendance.objects.create(
                employee=employee,
                work_date=work_date,
                hours_worked=hours_worked,
                attendance_status=status
            )
            messages.success(request, f"Attendance log committed for {employee.user.get_full_name()}.")
        except Employee.DoesNotExist:
            messages.error(request, "Employee row profile entry not found.")
        return redirect('attendance_tracker')

    employees = Employee.objects.all().select_related('user')
    attendance_records = Attendance.objects.all().select_related('employee__user').order_by('-work_date')[:15]
    return render(request, 'payroll/attendance_tracker.html', {
        'employees': employees,
        'attendance_records': attendance_records
    })


@login_required
def leave_manager(request):
    if request.method == 'POST':
        if is_admin_user(request.user) and 'update_status' in request.POST:
            leave_id = request.POST.get('leave_id')
            new_status = request.POST.get('status')
            Leave.objects.filter(pk=leave_id).update(status=new_status)
            messages.success(request, "Leave state modified successfully.")
            return redirect('leave_manager')

        elif request.user.profile.role == 'employee':
            try:
                employee = request.user.employee_profile
                start_date = datetime.strptime(request.POST.get('start_date'), '%Y-%m-%d').date()
                end_date = datetime.strptime(request.POST.get('end_date'), '%Y-%m-%d').date()
                total_days = (end_date - start_date).days + 1

                Leave.objects.create(
                    employee=employee,
                    leave_type=request.POST.get('leave_type'),
                    start_date=start_date,
                    end_date=end_date,
                    total_days=total_days,
                    reason=request.POST.get('reason'),
                    status='Pending'
                )
                messages.success(request, "Leave submission uploaded successfully.")
            except Exception:
                messages.error(request, "Failed to compute timelines. Verify parameters.")
            return redirect('leave_manager')

    if is_admin_user(request.user):
        leaves = Leave.objects.all().select_related('employee__user').order_by('-date_requested')
    else:
        leaves = Leave.objects.filter(employee=request.user.employee_profile).order_by('-date_requested')

    return render(request, 'payroll/leave_manager.html', {'leaves': leaves})


@login_required
def payroll_computation(request):
    if not is_admin_user(request.user):
        return redirect('staff_dashboard')

    if request.method == 'POST':
        emp_id = request.POST.get('employee_id')
        start_date = request.POST.get('period_start')
        end_date = request.POST.get('period_end')

        try:
            employee = Employee.objects.get(pk=emp_id)
            gross = float(employee.salary)
            deductions = gross * 0.12
            net = gross - deductions

            payroll = Payroll.objects.create(
                employee=employee,
                payroll_period_start=start_date,
                payroll_period_end=end_date,
                gross_salary=gross,
                deductions=deductions,
                net_salary=net,
                payroll_status='Completed'
            )

            Payslip.objects.create(
                payroll=payroll,
                issue_date=timezone.now().date(),
                remarks=f"Automated system run processing cycle executed on {timezone.now().date()}."
            )
            messages.success(request,
                             f"Payroll accounting ledger structured successfully for {employee.user.get_full_name()}!")
        except Exception as e:
            messages.error(request, f"Transactional computation fault: {str(e)}")
        return redirect('payroll_computation')

    employees = Employee.objects.all().select_related('user')
    payrolls = Payroll.objects.all().select_related('employee__user').order_by('-payroll_id')
    return render(request, 'payroll/payroll_computation.html', {
        'employees': employees,
        'payrolls': payrolls
    })


@login_required
def view_payslip(request, payroll_id):
    try:
        payroll = Payroll.objects.select_related('employee__user', 'payslip').get(pk=payroll_id)
        if request.user.profile.role == 'employee' and payroll.employee != request.user.employee_profile:
            return redirect('staff_dashboard')
        return render(request, 'payroll/view_payslip.html', {'payroll': payroll})
    except Payroll.DoesNotExist:
        messages.error(request, "Target invoice reference index could not be located.")
        return redirect('admin_dashboard' if request.user.profile.role == 'admin' else 'staff_dashboard')


# --- 👥 EMPLOYEE END-USER PANEL WORKSPACE ---
@login_required
def staff_dashboard(request):
    if is_admin_user(request.user):
        return redirect('admin_dashboard')

    try:
        employee = request.user.employee_profile
    except Employee.DoesNotExist:
        messages.error(request, "Employee profile record missing.")
        return redirect('logout')

    if request.method == 'POST' and 'clock_in' in request.POST:
        work_date = request.POST.get('work_date')
        hours_worked = request.POST.get('hours_worked', 8.0)

        already_logged = Attendance.objects.filter(employee=employee, work_date=work_date).exists()
        if already_logged:
            messages.warning(request, f"You have already submitted an attendance log for {work_date}.")
        else:
            Attendance.objects.create(
                employee=employee,
                work_date=work_date,
                hours_worked=hours_worked,
                attendance_status='Present'
            )
            messages.success(request, f"Attendance for {work_date} successfully logged!")
        return redirect('staff_dashboard')

    my_payrolls = Payroll.objects.filter(employee=employee).order_by('-payroll_id')
    my_attendance = Attendance.objects.filter(employee=employee).order_by('-work_date')[:10]

    context = {
        'my_payrolls': my_payrolls,
        'my_attendance': my_attendance,
    }
    return render(request, 'payroll/staff_dashboard.html', context)


# --- 🚪 LOGOUT SYSTEM DESTRUCTION PIPELINE ---
def logout_view(request):
    """Destroys the user session and redirects to the login screen."""
    logout(request)
    return redirect('login')