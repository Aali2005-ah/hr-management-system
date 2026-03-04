from django.urls import path
from . import views

urlpatterns = [

    # WELCOME SIDE
    path('', views.index, name='index'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),

    # EMPLOYEE
    path('employee/login/', views.employee_login, name='employee_login'),
    path('employee/announcement/', views.employee_announcement, name='employee_announcement'),
    path('employee/logout/', views.employee_logout, name='employee_logout'),

    # HR LOGIN
    path('hr/login/', views.hr_login, name='hr_login'),
    path('hr/logout/', views.hr_logout, name='logout'),

    # HR DASHBOARD
    path('hr/dashboard/', views.dashboard, name='dashboard'),
    path('hr/profile/', views.profile, name='profile'),

    # EMPLOYEE MANAGEMENT
    path('hr/add-employee/', views.add_employee, name='add_employee'),
    path('hr/view-employee/', views.view_employee, name='view_employee'),
    path('hr/update-employee/<int:id>/', views.update_employee, name='update_employee'),
    path('hr/employee-detail/<int:id>/', views.employee_detail, name='employee_detail'),
    path('hr/delete-employee/<int:id>/', views.delete_employee, name='delete_employee'),
    path('hr/employee/<int:id>/', views.employee_detail, name='employee_detail'),


    # ANNOUNCEMENT
    path('hr/add-announcement/', views.add_announcement, name='add_announcement'),
    path('hr/view-announcement/', views.view_announcement, name='view_announcement'),
    path('edit-announcement/<int:id>/', views.edit_announcement, name='edit_announcement'),
    path('delete-announcement/<int:id>/', views.delete_announcement, name='delete_announcement'),


    # ATTENDANCE
    path('hr/attendance/', views.attendance_view, name='attendance'),
    path('clear-attendance/', views.clear_attendance, name='clear_attendance'),


    # JOB ROLE SUMMARY
    path('hr/jobrole-summary/', views.jobrole_summary, name='jobrole_summary'),
    path('role/<int:role_id>/', views.view_role_employees, name='view_role_employees'),


]
