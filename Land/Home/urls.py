from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),   # root URL for the app
    path('register/', views.customer_register, name='customer_register'),
    path('login/', views.customer_login, name='customer_login'),
    path('customer_dashboard/', views.customer_dashboard, name='customer_dashboard'),
    path('logout/', views.customer_logout, name='customer_logout'),
    path('customer_dashboard', views.customer_dashboard, name='customer_dashboard'),
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('create_subregistrar/', views.create_subregistrar, name='create_subregistrar'),
    path('registrar_login/', views.registrar_login, name='registrar_login'),
    path('registrar_dashboard/', views.registrar_dashboard, name='registrar_dashboard'),
    path('customer/submit-transaction/', views.submit_transaction, name='submit_transaction'),
    path('property-valuation/', views.property_valuation, name='property_valuation'),
    path('get-localities/', views.get_localities_ajax, name='get_localities'),
    path("applications/", views.applications_list, name="applications_list"),
    path('application/<int:pk>/', views.application_detail, name='application_detail'),
    path('subregistrar/<int:pk>/edit/', views.edit_subregistrar, name='edit_subregistrar'),
    path('subregistrar/<int:pk>/delete/', views.delete_subregistrar, name='delete_subregistrar'),
    
]
