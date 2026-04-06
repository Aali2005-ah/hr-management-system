from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import update_session_auth_hash,authenticate, login
from django.contrib import messages
from .models import *
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta, time
from django.db.models import Prefetch
from django.db.models import Count
from django.db.models import Sum

EMPLOYEE_COMMON_PASSWORD = "emp123"


# ---------------- WELCOME ----------------
def index(request):
    return render(request, 'welcome/index.html')


def about(request):
    return render(request, 'welcome/about.html')


def contact(request):
    return render(request, 'welcome/contact.html')


# ---------------- EMPLOYEE LOGIN ----------------
def employee_login(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        password = request.POST.get('password')

        if password == EMPLOYEE_COMMON_PASSWORD:
            employee = Employee.objects.filter(name=name).first()

            if employee:
                request.session['employee_name'] = employee.name
                return redirect('employee_announcement')

        return render(request, 'welcome/employee_login.html', {
            'error': 'Wrong name or password'
        })

    return render(request, 'welcome/employee_login.html')



def employee_announcement(request):
    if not request.session.get('employee_name'):
        return redirect('employee_login')

    # Delete expired (non-permanent)
    Announcement.objects.filter(
        permanent=False,
        display_until__lt=timezone.now()
    ).delete()

    announcements = Announcement.objects.filter(
        permanent=True
    ) | Announcement.objects.filter(
        display_until__gte=timezone.now()
    )

    announcements = announcements.order_by('-created_at')

    return render(request, 'employee/announcement.html', {
        'employee_name': request.session.get('employee_name'),
        'announcements': announcements
    })



def employee_logout(request):
    request.session.flush()
    return redirect('index')


# ---------------- HR LOGIN ----------------
def hr_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid username or Password")

    return render(request, 'welcome/hr_login.html')


def hr_logout(request):
    logout(request)
    return redirect('index')


# ---------------- HR DASHBOARD ----------------
from django.db.models import Sum, Count
from django.utils.timezone import now
from datetime import timedelta
@login_required
def dashboard(request):

    today = now().date()
    current_month = today.month
    current_year = today.year

    # ---------------- BASIC COUNTS ----------------
    total_emp = Employee.objects.count()
    total_roles = JobRole.objects.count()

    total_salary = Employee.objects.aggregate(
        total=Sum('salary')
    )['total'] or 0

    # ---------------- TODAY ATTENDANCE ----------------
    present_today = Attendance.objects.filter(
        date=today,
        status='Present'
    ).count()

    absent_today = Attendance.objects.filter(
        date=today,
        status='Absent'
    ).count()

    attendance_percentage = round(
        (present_today / total_emp) * 100
    ) if total_emp > 0 else 0

    # ---------------- JOINED THIS MONTH ----------------
    joined_this_month = Employee.objects.filter(
        joining_date__month=current_month,
        joining_date__year=current_year
    ).count()

    # ---------------- UPCOMING BIRTHDAYS ----------------
    next_week = today + timedelta(days=7)

    upcoming_birthdays = Employee.objects.filter(
        dob__month=today.month,
        dob__day__gte=today.day,
        dob__day__lte=next_week.day
    ).count()

    # ---------------- 🔥 EMPLOYEE OF THE MONTH ----------------
    monthly_attendance = Attendance.objects.filter(
        status='Present',
        date__month=current_month,
        date__year=current_year
    ).values('employee').annotate(
        total_present=Count('id')
    ).order_by('-total_present')

    if monthly_attendance.exists():

        top_data = monthly_attendance.first()
        top_employee = Employee.objects.get(id=top_data['employee'])

        # total working days in this month (attendance marked days)
        total_working_days = Attendance.objects.filter(
            date__month=current_month,
            date__year=current_year
        ).values('date').distinct().count()

        if total_working_days > 0:
            emp_attendance_percent = round(
                (top_data['total_present'] / total_working_days) * 100
            )
        else:
            emp_attendance_percent = 0
    else:
        top_employee = None
        emp_attendance_percent = 0

    # ---------------- ANNOUNCEMENTS ----------------
    Announcement.objects.filter(
        permanent=False,
        display_until__lt=now()
    ).delete()

    active_announcements = Announcement.objects.filter(
        permanent=True
    ) | Announcement.objects.filter(
        display_until__gte=now()
    )

    total_ann = active_announcements.count()
    recent_ann = active_announcements.order_by('-created_at')[:5]

    context = {
        'total_emp': total_emp,
        'total_roles': total_roles,
        'total_salary': total_salary,
        'present_today': present_today,
        'absent_today': absent_today,
        'attendance_percentage': attendance_percentage,
        'joined_this_month': joined_this_month,
        'upcoming_birthdays': upcoming_birthdays,
        'total_ann': total_ann,
        'recent_ann': recent_ann,
        'top_employee': top_employee,
        'emp_attendance_percent': emp_attendance_percent,
    }

    return render(request, 'hr/dashboard.html', context)


# ---------------- HR PROFILE ----------------
@login_required
def profile(request):

    profile, created = HRProfile.objects.get_or_create(user=request.user)

    step = request.GET.get("step")
    error = ""
    success = ""

    # PHOTO UPDATE
    if request.method == "POST" and request.FILES.get("photo"):
        profile.photo = request.FILES["photo"]
        profile.save()
        return redirect("profile")

    # NAME UPDATE
    if request.method == "POST" and "update_name" in request.POST:
        request.user.username = request.POST.get("name")
        request.user.save()
        return redirect("profile")

    # EMAIL UPDATE
    if request.method == "POST" and "update_email" in request.POST:
        request.user.email = request.POST.get("email")
        request.user.save()
        return redirect("profile")

    # STEP 1 – CHECK OLD PASSWORD
    if request.method == "POST" and "check_old" in request.POST:
        old = request.POST.get("old_password")

        if request.user.check_password(old):
            request.session["password_verified"] = True
            return redirect("/hr/profile?step=2")
        else:
            step = "1"
            error = "Wrong Password"

    # STEP 2 – CHANGE PASSWORD
    if request.method == "POST" and "change_password" in request.POST:

        if request.session.get("password_verified"):

            new = request.POST.get("new_password")
            confirm = request.POST.get("confirm_password")

            if new == confirm:
                user = request.user
                user.set_password(new)
                user.save()

                update_session_auth_hash(request, user)

                request.session["password_verified"] = False
                success = "Password Updated Successfully"
                step = None

            else:
                step = "2"
                error = "Passwords Do Not Match"

    return render(request, "hr/profile.html", {
        "profile": profile,
        "step": step,
        "error": error,
        "success": success
    })


# ---------------- EMPLOYEE CRUD ----------------
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from datetime import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from .models import Employee, JobRole  # Make sure JobRole is imported
from datetime import datetime

from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Employee, JobRole

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from datetime import datetime
from .models import Employee, JobRole

@login_required
def add_employee(request):
    roles = JobRole.objects.all()
    form_data = {}

    if request.method == 'POST':
        form_data = {
            'name': request.POST.get('name', ''),
            'phone': request.POST.get('phone', ''),
            'email': request.POST.get('email', ''),
            'place': request.POST.get('place', ''),
            'mode': request.POST.get('mode', ''),
            'job_role': request.POST.get('job_role', ''),
            'dob': request.POST.get('dob', ''),
            'joining': request.POST.get('joining', ''),
            'salary': request.POST.get('salary', ''),
        }

        valid = True

        # Duplicate Email Check
        if Employee.objects.filter(email=form_data['email']).exists():
            messages.error(
                request,
                f"The email '{form_data['email']}' is already registered to another employee.",
                extra_tags='add_employee'
            )
            valid = False

        # Duplicate Phone Check
        if Employee.objects.filter(phone=form_data['phone']).exists():
            messages.error(
                request,
                f"The phone number '{form_data['phone']}' is already in use.",
                extra_tags='add_employee'
            )
            valid = False

        # Required Fields Check
        if not form_data['name'] or not form_data['job_role']:
            messages.error(
                request, 
                "Please fill in all required fields.",
                extra_tags='add_employee'
            )
            valid = False

        if valid:
            try:
                selected_role = JobRole.objects.get(id=form_data['job_role'])

                new_employee = Employee(
                    name=form_data['name'],
                    phone=form_data['phone'],
                    email=form_data['email'],
                    place=form_data['place'],
                    mode_of_work=form_data['mode'],
                    job_role=selected_role,
                    dob=form_data['dob'],
                    joining_date=form_data['joining'],
                    salary=int(form_data['salary']) if form_data['salary'] else 0,
                    photo=request.FILES.get('photo')
                )

                new_employee.save()

                messages.success(
                    request,
                    f"Employee {new_employee.name} added successfully!",
                    extra_tags='add_employee'
                )

                return redirect('view_employee')

            except JobRole.DoesNotExist:
                messages.error(
                    request, 
                    "Selected Job Role does not exist.",
                    extra_tags='add_employee'
                )
            except Exception as e:
                messages.error(
                    request,
                    f"An unexpected error occurred: {str(e)}",
                    extra_tags='add_employee'
                )

    return render(request, 'hr/add_employee.html', {
        'roles': roles,
        'form_data': form_data
    })

@login_required
def view_employee(request):
    try:
        roles = JobRole.objects.all()
        role_data = {}

        for role in roles:
            employees = Employee.objects.filter(job_role=role).order_by('name')
            role_data[role] = employees

        return render(request, 'hr/view_employee.html', {
            'role_data': role_data
        })
    except Exception as e:
        messages.error(
            request, 
            f'Error loading employees: {str(e)}',
            extra_tags='view_employee'
        )
        return render(request, 'hr/view_employee.html', {'role_data': {}})

@login_required
def employee_detail(request, id):
    employee = get_object_or_404(Employee, id=id)
    return render(request, "hr/employee_detail.html", {
        "employee": employee
    })

@login_required
def update_employee(request, id):
    employee = get_object_or_404(Employee, id=id)
    roles = JobRole.objects.all()
    error_messages = {}
    form_data = {}

    if request.method == "POST":
        # Collect form data
        form_data = {
            'name': request.POST.get('name', ''),
            'phone': request.POST.get('phone', ''),
            'email': request.POST.get('email', ''),
            'place': request.POST.get('place', ''),
            'mode': request.POST.get('mode', ''),
            'job_role': request.POST.get('job_role', ''),
            'dob': request.POST.get('dob', ''),
            'joining': request.POST.get('joining', ''),
            'salary': request.POST.get('salary', ''),
        }
        
        # Validation
        if not form_data['name']:
            error_messages['name'] = 'Name is required'
        
        if not form_data['phone']:
            error_messages['phone'] = 'Phone number is required'
        elif not form_data['phone'].isdigit() or len(form_data['phone']) != 10:
            error_messages['phone'] = 'Phone number must be 10 digits'
        
        if not form_data['email']:
            error_messages['email'] = 'Email is required'
        else:
            try:
                validate_email(form_data['email'])
                # Check if email already exists (excluding current employee)
                if Employee.objects.filter(email=form_data['email']).exclude(id=id).exists():
                    error_messages['email'] = 'This email is already registered'
            except ValidationError:
                error_messages['email'] = 'Enter a valid email address'
        
        if not form_data['place']:
            error_messages['place'] = 'Place is required'
        
        if not form_data['mode']:
            error_messages['mode'] = 'Mode of work is required'
        
        if not form_data['job_role']:
            error_messages['job_role'] = 'Job role is required'
        
        # Date validation
        if not form_data['dob']:
            error_messages['dob'] = 'Date of birth is required'
        else:
            try:
                datetime.strptime(form_data['dob'], '%Y-%m-%d')
            except ValueError:
                error_messages['dob'] = 'Invalid date format for Date of Birth'
        
        if not form_data['joining']:
            error_messages['joining'] = 'Joining date is required'
        else:
            try:
                datetime.strptime(form_data['joining'], '%Y-%m-%d')
            except ValueError:
                error_messages['joining'] = 'Invalid date format for Joining Date'
        
        if not form_data['salary']:
            error_messages['salary'] = 'Salary is required'
        elif not form_data['salary'].isdigit():
            error_messages['salary'] = 'Salary must be a number'
        
        # If no errors, update the employee
        if not error_messages:
            try:
                employee.name = form_data['name']
                employee.phone = form_data['phone']
                employee.email = form_data['email']
                employee.place = form_data['place']
                employee.mode_of_work = form_data['mode']
                
                # Set dates
                if form_data['dob']:
                    employee.dob = form_data['dob']
                if form_data['joining']:
                    employee.joining_date = form_data['joining']
                
                employee.salary = form_data['salary']
                
                # Get job role
                try:
                    role_id = int(form_data['job_role'])
                    employee.job_role = JobRole.objects.get(id=role_id)
                except (ValueError, JobRole.DoesNotExist):
                    error_messages['job_role'] = 'Invalid job role selected'
                    raise Exception("Invalid job role")
                
                # Handle photo upload
                if request.FILES.get("photo"):
                    # Delete old photo if it exists
                    if employee.photo:
                        employee.photo.delete(save=False)
                    employee.photo = request.FILES.get("photo")
                
                employee.save()
                messages.success(
                    request, 
                    'Employee updated successfully!',
                    extra_tags='update_employee'
                )
                return redirect("view_employee")
                
            except Exception as e:
                messages.error(
                    request, 
                    f'Error updating employee: {str(e)}',
                    extra_tags='update_employee'
                )
                # Stay on the same page with form data
                return render(request, "hr/update_employee.html", {
                    "employee": employee,
                    "roles": roles,
                    "error_messages": error_messages,
                    "form_data": form_data
                })
        else:
            # If there are validation errors, stay on the same page
            messages.error(
                request, 
                'Please correct the errors below.',
                extra_tags='update_employee'
            )
    
    # For GET request, populate form_data with employee data
    else:
        form_data = {
            'name': employee.name,
            'phone': employee.phone,
            'email': employee.email,
            'place': employee.place,
            'mode': employee.mode_of_work,
            'job_role': employee.job_role_id if employee.job_role else '',
            'dob': employee.dob.strftime('%Y-%m-%d') if employee.dob else '',
            'joining': employee.joining_date.strftime('%Y-%m-%d') if employee.joining_date else '',
            'salary': employee.salary,
        }

    return render(request, "hr/update_employee.html", {
        "employee": employee,
        "roles": roles,
        "error_messages": error_messages,
        "form_data": form_data
    })

@login_required
def delete_employee(request, id):
    employee = get_object_or_404(Employee, id=id)
    
    if request.method == "POST":
        try:
            # Delete photo if it exists
            if employee.photo:
                employee.photo.delete()
            employee.delete()
            messages.success(
                request, 
                'Employee deleted successfully!',
                extra_tags='delete_employee'
            )
            return redirect('view_employee')
        except Exception as e:
            messages.error(
                request, 
                f'Error deleting employee: {str(e)}',
                extra_tags='delete_employee'
            )
    
    return render(request, 'hr/delete_employee.html', {
        "employee": employee
    })
# ---------------- ANNOUNCEMENT ----------------
@login_required

def add_announcement(request):
    if request.method == "POST":
        title = request.POST.get("title")
        content = request.POST.get("content")
        days = int(request.POST.get("days", 0))
        hours = int(request.POST.get("hours", 0))
        minutes = int(request.POST.get("minutes", 0))
        permanent = request.POST.get("permanent") == "on"

        created_time = timezone.now()

        display_until = None
        if not permanent:
            duration = timedelta(days=days, hours=hours, minutes=minutes)
            display_until = created_time + duration

        Announcement.objects.create(
            title=title,
            content=content,
            created_at=created_time,
            display_until=display_until,
            permanent=permanent
        )

        return redirect("view_announcement")

    return render(request, "hr/add_announcement.html")


@login_required

def view_announcement(request):
    announcements = Announcement.objects.all().order_by('-created_at')
    return render(request, 'hr/view_announcement.html', {
        'announcements': announcements,
        'now': timezone.now()
    })





def delete_announcement(request, id):
    announcement = get_object_or_404(Announcement, id=id)
    announcement.delete()
    return redirect('view_announcement')



def edit_announcement(request, id):
    announcement = Announcement.objects.get(id=id)

    # Default selected values
    selected_days = 0
    selected_hours = 0
    selected_minutes = 0

    if announcement.display_until and not announcement.permanent:
        remaining = announcement.display_until - announcement.created_at
        total_seconds = int(remaining.total_seconds())

        selected_days = total_seconds // 86400
        selected_hours = (total_seconds % 86400) // 3600
        selected_minutes = (total_seconds % 3600) // 60

    if request.method == "POST":
        announcement.title = request.POST.get("title")
        announcement.content = request.POST.get("content")
        permanent = request.POST.get("permanent") == "on"

        if permanent:
            announcement.permanent = True
            announcement.display_until = None
        else:
            days = int(request.POST.get("days", 0))
            hours = int(request.POST.get("hours", 0))
            minutes = int(request.POST.get("minutes", 0))

            duration = timedelta(days=days, hours=hours, minutes=minutes)
            announcement.display_until = timezone.now() + duration
            announcement.permanent = False

        announcement.save()
        return redirect("view_announcement")

    return render(request, "hr/edit_announcement.html", {
        "announcement": announcement,
        "selected_days": selected_days,
        "selected_hours": selected_hours,
        "selected_minutes": selected_minutes
    })






# ---------------- ATTENDANCE ----------------


@login_required
def attendance_view(request):

    now = timezone.localtime()
    today = now.date()

    total_employees = Employee.objects.count()
    marked_count = Attendance.objects.filter(date=today).count()

    already_marked = (
        total_employees > 0 and
        marked_count == total_employees
    )

    # 🔒 BEFORE 10 AM
    if now.time() < time(10, 0) and not already_marked:
        return render(request, 'hr/attendance_locked.html', {
            "message": "Attendance will open at 10:00 AM.",
            "show_clear": False
        })

    # 🔒 AFTER SUBMISSION
    if already_marked:
        return render(request, 'hr/attendance_locked.html', {
            "message": "Attendance already submitted for today.",
            "show_clear": True
        })

    # ✅ GET ALL JOB ROLES (ALWAYS SHOW ALL)
    job_roles = JobRole.objects.all()

    role_data = {}

    for role in job_roles:
        employees = Employee.objects.filter(job_role=role).order_by(
            '-mode_of_work',  # Full Time first
            'name'
        )

        # Manual correct order
        full_time = employees.filter(mode_of_work="Full Time")
        part_time = employees.filter(mode_of_work="Part Time")
        intern = employees.filter(mode_of_work="Intern")

        ordered = list(full_time) + list(part_time) + list(intern)

        role_data[role] = ordered

    # ✅ SUBMIT
    if request.method == "POST":
        for role in role_data.values():
            for emp in role:
                status = "Present" if request.POST.get(f"status_{emp.id}") else "Absent"

                Attendance.objects.update_or_create(
                    employee=emp,
                    date=today,
                    defaults={"status": status}
                )

        return render(request, 'hr/attendance_locked.html', {
            "message": "Attendance successfully submitted.",
            "show_clear": True
        })

    return render(request, 'hr/attendance.html', {
        "role_data": role_data,
        "today": today
    })





@login_required
def clear_attendance(request):

    today = timezone.localtime().date()

    if not request.user.is_staff:
        return redirect('attendance')

    if request.method == "POST":
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=request.user.username,
            password=password
        )

        if user is not None and user.is_staff:
            Attendance.objects.filter(date=today).delete()
            return redirect('attendance')
        else:
            return render(request, 'hr/clear_attendance.html', {
                "error": "Incorrect HR password."
            })

    return render(request, 'hr/clear_attendance.html')




# ---------------- JOB ROLE SUMMARY ----------------


from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Employee, JobRole


@login_required
def jobrole_summary(request):

    job_roles = JobRole.objects.all()
    summary_data = []

    for role in job_roles:

        employees = Employee.objects.filter(job_role=role)

        total = employees.count()
        interns = employees.filter(mode_of_work="Intern").count()
        full_time = employees.filter(mode_of_work="Full Time").count()
        part_time = employees.filter(mode_of_work="Part Time").count()

        summary_data.append({
            "role": role,
            "total": total,
            "interns": interns,
            "full_time": full_time,
            "part_time": part_time,
        })

    context = {
        "summary_data": summary_data
    }

    return render(request, "hr/jobrole_summary.html", context)


@login_required
def view_role_employees(request, role_id):
    role = JobRole.objects.get(id=role_id)
    
    # Get the 'type' from the URL parameters (default to 'ALL')
    selected_type = request.GET.get('type', 'ALL')
    
    # Start with all employees for this role
    employees = Employee.objects.filter(job_role=role)
    
    # Apply filtering logic
    if selected_type != 'ALL':
        employees = employees.filter(mode_of_work=selected_type)

    return render(request, "hr/view_role_employees.html", {
        "role": role,
        "employees": employees,
        "selected_type": selected_type  # Pass this back to keep the dropdown selection
    })


