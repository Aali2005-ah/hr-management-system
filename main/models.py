from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.utils import timezone


# ---------------- JOB ROLE ----------------
class JobRole(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10)

    def __str__(self):
        return self.name


# ---------------- EMPLOYEE ----------------
# ---------------- EMPLOYEE ----------------
class Employee(models.Model):
    employee_id = models.CharField(max_length=20, unique=True, blank=True)
    name = models.CharField(max_length=100)
    phone = models.CharField(
        max_length=10,
        validators=[RegexValidator(r'^\d{10}$', 'Enter 10 digit phone number')]
    )
    email = models.EmailField(unique=True)  # Added unique=True
    place = models.CharField(max_length=100)
    
    MODE_CHOICES = [
        ('Intern', 'Intern'),
        ('Part Time', 'Part Time'),
        ('Full Time', 'Full Time'),
    ]
    
    mode_of_work = models.CharField(max_length=20, choices=MODE_CHOICES)
    job_role = models.ForeignKey(JobRole, on_delete=models.CASCADE)
    dob = models.DateField()
    joining_date = models.DateField()
    salary = models.IntegerField()
    photo = models.ImageField(upload_to='employees/', null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.employee_id:
            role_code = self.job_role.code
            count = Employee.objects.filter(job_role=self.job_role).count() + 1
            self.employee_id = f"{role_code}{count}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

# ---------------- 
from django.utils import timezone

class Announcement(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    display_until = models.DateTimeField(null=True, blank=True)
    permanent = models.BooleanField(default=False)

    def is_active(self):
        if self.permanent:
            return True
        if self.display_until:
            return self.display_until >= timezone.now()
        return False


    def __str__(self):
        return self.title


# ---------------- ATTENDANCE ----------------
class Attendance(models.Model):

    STATUS_CHOICES = [
        ('Present', 'Present'),
        ('Absent', 'Absent'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    date = models.DateField(default=timezone.now)

    def __str__(self):
        return f"{self.employee.name} - {self.date}"



# ---------------- HR PROFILE ----------------
class HRProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    photo = models.ImageField(upload_to='hr_photos/', null=True, blank=True)

    def __str__(self):
        return self.user.username
