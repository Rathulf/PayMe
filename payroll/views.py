from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django import forms
from django.contrib.auth.models import User
from .models import Profile, Employee, Payroll, Leave, Attendance, Payslip


class CustomRegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)
    contact_no = forms.CharField(max_length=20, required=False)

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if len(username) < 6:
            raise forms.ValidationError("The username must be at least 6 characters long.")
        return username


def register_view(request):
    if request.method == 'POST':
        form = CustomRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.first_name = form.cleaned_data.get('first_name')
            user.last_name = form.cleaned_data.get('last_name')
            user.email = form.cleaned_data.get('email')

            role_selected = request.POST.get('role', 'employee')
            user.profile.role = role_selected
            user.profile.contact_no = form.cleaned_data.get('contact_no')

            if role_selected == 'admin':
                user.is_staff = True
            user.save()

            # If newly created role is an employee, update baseline details
            if role_selected == 'employee':
                emp_profile = user.employee_profile
                emp_profile.department = request.POST.get('department', 'General')
                emp_profile.position = request.POST.get('position', 'Staff')
                emp_profile.salary = request.POST.get('salary', 0.00)
                emp_profile.save()

            messages.success(request, "Registration successful! Please log in below.")
            return redirect('login')
        else:
            messages.error(request, "Registration failed. Please correct the errors below.")
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


@login_required
def admin_dashboard(request):
    if request.user.profile.role != 'admin':
        return redirect('staff_dashboard')
    context = {
        'total_employees': Employee.objects.count(),
        'total_payroll_month': 24500.00,
        'pending_payslips': Payroll.objects.filter(payroll_status='Pending').count(),
        'recent_activities': Payroll.objects.all().order_by('-payroll_id')[:5]
    }
    return render(request, 'payroll/admin_dashboard.html', context)


@login_required
def manage_employees(request):
    employees = Employee.objects.all()
    return render(request, 'payroll/manage_employees.html', {'employees': employees})


@login_required
def payroll_computation(request):
    return render(request, 'payroll/payroll_computation.html')


@login_required
def admin_payslips(request):
    payslips = Payslip.objects.all()
    return render(request, 'payroll/admin_payslips.html', {'payslips': payslips})


@login_required
def admin_reports(request):
    return render(request, 'payroll/admin_reports.html')


@login_required
def staff_dashboard(request):
    if request.user.profile.role == 'admin':
        return redirect('admin_dashboard')
    return render(request, 'payroll/staff_dashboard.html')


def logout_view(request):
    logout(request)
    return redirect('login')