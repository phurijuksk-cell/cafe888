from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'), 
    path('checkout/', views.checkout, name='checkout'),
    path('queue/', views.queue, name='queue'),
    path('profile/', views.profile, name='profile'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),

    path('login/', views.custom_login, name='login'),
    path('register/', views.custom_register, name='register'),
    path('logout/', views.custom_logout, name='logout'),
    
    path('delete-account/', views.delete_account, name='delete_account'),
    path('clear-queue/', views.clear_queue, name='clear_queue'),

    path('staff/', views.staff_dashboard, name='staff_dashboard'),
    path('update-queue/<int:queue_id>/<str:new_status>/', views.update_queue_status, name='update_queue_status'),
    path('update-payment/<int:queue_id>/<str:new_status>/', views.update_payment_status, name='update_payment_status'),

    # [เพิ่มใหม่] หน้าจอสำหรับให้ Admin เพิ่มพนักงาน
    path('add-staff/', views.add_staff, name='add_staff'),

    path('api/check-queue/', views.api_check_queue, name='api_check_queue'),
]