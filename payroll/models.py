from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    ROLE_CHOICES = (
        ('superadmin', 'System Superadmin'),
        ('admin', 'Department Admin'),
        ('hr_manager', 'HR Manager'),
        ('payroll_officer', 'Payroll Officer'),
        ('employee', 'Regular Employee'),
    )
    STATUS_CHOICES = (
        ('active', 'Active Personnel'),
        ('inactive', 'Suspended/Inactive'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='inactive')
    contact_no = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"


class Employee(models.Model):
    employee_id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee_profile')
    department = models.CharField(max_length=100, default='Operations')
    position = models.CharField(max_length=100, default='Junior Associate')
    salary = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    date_hired = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.position})"


class AdminProfile(models.Model):
    admin_id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin_profile')
    managed_department = models.CharField(max_length=100, default='General Operations')

    def __str__(self):
        return f"Manager: {self.user.get_full_name()} [{self.managed_department}]"


class Attendance(models.Model):
    STATUS_CHOICES = (('Present', 'Present'), ('Absent', 'Absent'), ('Late', 'Late'))
    attendance_id = models.AutoField(primary_key=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    work_date = models.DateField()

    # LIVE TRACKING
    clock_in_time = models.DateTimeField(null=True, blank=True)
    clock_out_time = models.DateTimeField(null=True, blank=True)
    is_clocked_out = models.BooleanField(default=False)

    # Overtime Calculation
    hours_worked = models.DecimalField(max_digits=4, decimal_places=2, default=0.00)
    overtime_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0.00)

    attendance_status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Present')

    class Meta:
        unique_together = ('employee', 'work_date')

    def __str__(self):
        return f"{self.employee.user.last_name} - {self.work_date}"


class Leave(models.Model):
    LEAVE_CHOICES = (('Sick Leave', 'Sick Leave'), ('Vacation Leave', 'Vacation Leave'),
                     ('Emergency Leave', 'Emergency Leave'))
    STATUS_CHOICES = (('Pending', 'Pending Review'), ('Approved', 'Approved'), ('Rejected', 'Rejected'))
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    leave_type = models.CharField(max_length=30, choices=LEAVE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    total_days = models.IntegerField()
    reason = models.TextField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Pending')
    date_requested = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee.user.last_name} - {self.leave_type} ({self.status})"


class Payroll(models.Model):
    STATUS_CHOICES = (('Pending', 'Pending Execution'), ('Completed', 'Settled/Completed'))

    # Flexible business cycles
    CYCLE_CHOICES = (
        ('semi_monthly', 'Semi-Monthly (1st-15th & 16th-End)'),
        ('bi_weekly', 'Bi-Weekly (Every Two Weeks)'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    )

    payroll_id = models.AutoField(primary_key=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)

    # Cycle field
    processing_cycle = models.CharField(max_length=20, choices=CYCLE_CHOICES, default='semi_monthly')

    payroll_period_start = models.DateField()
    payroll_period_end = models.DateField()
    gross_salary = models.DecimalField(max_digits=10, decimal_places=2)
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    net_salary = models.DecimalField(max_digits=10, decimal_places=2)
    payroll_status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Pending')

    def __str__(self):
        return f"Payroll #{self.payroll_id} - {self.employee.user.last_name} ({self.get_processing_cycle_display()})"


class Payslip(models.Model):
    payslip_id = models.AutoField(primary_key=True)
    payroll = models.OneToOneField(Payroll, on_delete=models.CASCADE, related_name='payslip')
    issue_date = models.DateField(auto_now_add=True)
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Payslip Voucher #{self.payslip_id}"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()