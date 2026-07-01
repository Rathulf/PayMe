from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Administrator (HR)'),
        ('employee', 'Employee / Staff'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='employee')
    employee_id = models.CharField(max_length=20, blank=True, null=True, unique=True)
    department = models.CharField(max_length=50, blank=True, null=True)
    base_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"


# Automated profile synchronization pipeline signals
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()