from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .models import JobRole


@receiver(post_migrate)
def create_default_job_roles(sender, **kwargs):
    default_roles = [
        ("Software Engineer", "SE"),
        ("Data Analyst", "DA"),
        ("HR Executive", "HR"),
        ("Marketing Manager", "MM"),
        ("Accountant", "ACC"),
        ("UI/UX Designer", "UX"),
        ("Backend Developer", "BD"),
        ("Frontend Developer", "FD"),
        ("Project Manager", "PM"),
        ("Business Analyst", "BA"),
    ]

    for name, code in default_roles:
        JobRole.objects.get_or_create(name=name, code=code)
