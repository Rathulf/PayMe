from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django import forms
from django.contrib.auth.models import User
from django.db.models import Sum
from .models import Profile, Employee, Payroll, Leave, Attendance, Payslip, AdminProfile


# CUSTOM REGISTRATION FORM (Public Side)
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


# ADMINISTRATIVE ACCESS GATEKEEPER
def is_admin_user(user):
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.role == 'admin'


# PUBLIC REGISTRATION VIEW
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

            messages.success(request, "Registration successful! Pending configuration.")
            return redirect('login')
        else:
            messages.error(request, "Registration failed. Correct validation errors.")
    else:
        form = CustomRegisterForm()
    return render(request, 'payroll/register.html', {'form': form})


# CENTRAL LOGIN AUTHENTICATION
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


# ADMIN WORKSPACE OVERVIEW
@login_required
def admin_dashboard(request):
    if not is_admin_user(request.user):
        return redirect('staff_dashboard')

    total_employees_count = Employee.objects.count()

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
        'total_payroll_month': f"{total_payroll_calc:,.2f}",
        'pending_payslips': pending_payslips_count,
        'recent_activities': recent_activities_list,
    }
    return render(request, 'payroll/admin_dashboard.html', context)


# TWIN TABLE WORKFORCE AND ADMIN MANAGER
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


# REGULAR CORE LAYOUT VIEWS
@login_required
def payroll_computation(request):
    if not is_admin_user(request.user): return redirect('staff_dashboard')
    return render(request, 'payroll/payroll_computation.html')


@login_required
def admin_payslips(request):
    if not is_admin_user(request.user): return redirect('staff_dashboard')
    payslips = Payslip.objects.all()
    return render(request, 'payroll/admin_payslips.html', {'payslips': payslips})


@login_required
def admin_reports(request):
    if not is_admin_user(request.user): return redirect('staff_dashboard')
    return render(request, 'payroll/admin_reports.html')


@login_required
def staff_dashboard(request):
    if is_admin_user(request.user): return redirect('admin_dashboard')
    return render(request, 'payroll/staff_dashboard.html')


def logout_view(request):
    logout(request)
    return redirect('login')