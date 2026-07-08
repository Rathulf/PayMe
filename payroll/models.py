from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# 1. EXTENDED USER PROFILE MODEL
class Profile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('employee', 'Employee'),
    ]
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    contact_no = models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='employee')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='active')

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"


# 2. EXPANDED ADMIN MODEL (With Classifications)
class AdminProfile(models.Model):
    CLASSIFICATION_CHOICES = [
        ('business_owner', 'Business Owner'),
        ('hr_manager', 'HR Manager'),
        ('it_admin', 'IT Administrator'),
    ]

    admin_id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin_profile')
    admin_type = models.CharField(max_length=25, choices=CLASSIFICATION_CHOICES, default='hr_manager')
    managed_department = models.CharField(max_length=100, default='All Departments Scope')
    office_location = models.CharField(max_length=100, default='Main Headquarters')

    def __str__(self):
        return f"ADM-{self.admin_id:03d}: {self.user.username} ({self.get_admin_type_display()})"


# 3. EMPLOYEE MODEL
class Employee(models.Model):
    employee_id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee_profile')
    department = models.CharField(max_length=100)
    position = models.CharField(max_length=100)
    salary = models.DecimalField(max_digits=12, decimal_places=2)
    date_hired = models.DateField()

    def __str__(self):
        return f"EMP-{self.employee_id:05d}: {self.user.first_name} {self.user.last_name}"


# 4. LEAVE MODEL
class Leave(models.Model):
    leave_id = models.AutoField(primary_key=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leaves')
    leave_type = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()
    total_days = models.IntegerField()
    reason = models.TextField()
    status = models.CharField(max_length=20, default='Pending')
    date_requested = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Leave {self.leave_id} - {self.employee.user.username}"


# 5. ATTENDANCE MODEL
class Attendance(models.Model):
    attendance_id = models.AutoField(primary_key=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendances')
    work_date = models.DateField()
    hours_worked = models.DecimalField(max_digits=5, decimal_places=2)
    attendance_status = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.employee.user.username} - {self.work_date}"


# 6. PAYROLL MODEL
class Payroll(models.Model):
    payroll_id = models.AutoField(primary_key=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='payrolls')
    payroll_period_start = models.DateField()
    payroll_period_end = models.DateField()
    gross_salary = models.DecimalField(max_digits=12, decimal_places=2)
    deductions = models.DecimalField(max_digits=12, decimal_places=2)
    net_salary = models.DecimalField(max_digits=12, decimal_places=2)
    payroll_status = models.CharField(max_length=20)

    def __str__(self):
        return f"Payroll {self.payroll_id} - {self.employee.user.username}"


# 7. PAYSLIP MODEL
class Payslip(models.Model):
    payslip_id = models.AutoField(primary_key=True)
    payroll = models.OneToOneField(Payroll, on_delete=models.CASCADE, related_name='payslip')
    issue_date = models.DateField()
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Slip #{self.payslip_id} for Payroll {self.payroll_id}"


# 🌟 AUTOMATED PIPELINE SIGNALS
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()