from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django import forms  # For the custom validation rule
from django.contrib.auth.models import User
from .models import Profile


# 🌟 CUSTOM REGISTRATION FORM WITH USERNAME LENGTH CHECK
class CustomRegisterForm(UserCreationForm):
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if len(username) < 6:
            raise forms.ValidationError("The username must be at least 6 characters long.")
        return username


# 1. REGISTER VIEW
def register_view(request):
    if request.method == 'POST':
        form = CustomRegisterForm(request.POST)
        if form.is_valid():
            # Automatically hashes the password securely based on your settings.py rules
            user = form.save()

            # Extract custom registration profile parameters
            role_selected = request.POST.get('role', 'employee')
            emp_id = request.POST.get('employee_id', '')

            # Update the user profile model instance mapped via Django signals
            user.profile.role = role_selected
            user.profile.employee_id = emp_id if emp_id else None

            if role_selected == 'admin':
                user.is_staff = True

            user.save()
            messages.success(request, "Registration successful! Please log in below.")
            return redirect('login')  # 🚀 Redirects straight to the login screen on success!
        else:
            messages.error(request, "Registration failed. Please correct the errors below.")
    else:
        form = CustomRegisterForm()
    return render(request, 'payroll/register.html', {'form': form})


# 2. LOGIN VIEW
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)

            if user is not None:
                login(request, user)
                # 🚀 Dynamically redirects to the correct workspace dashboard based on user role
                if user.profile.role == 'admin':
                    return redirect('admin_dashboard')
                else:
                    return redirect('staff_dashboard')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, 'payroll/login.html', {'form': form})


# 3. ADMIN DASHBOARD VIEW
@login_required
def admin_dashboard(request):
    if request.user.profile.role != 'admin':
        return redirect('staff_dashboard')
    context = {
        'total_employees': Profile.objects.filter(role='employee').count(),
        'total_payroll_month': 24500.00,
        'pending_payslips': 5,
    }
    return render(request, 'payroll/admin_dashboard.html', context)


# 4. STAFF DASHBOARD VIEW
@login_required
def staff_dashboard(request):
    if request.user.profile.role == 'admin':
        return redirect('admin_dashboard')
    return render(request, 'payroll/staff_dashboard.html')


# 5. LOGOUT VIEW
def logout_view(request):
    logout(request)
    return redirect('login')