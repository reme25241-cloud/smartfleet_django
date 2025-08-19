from django.urls import path
from . import views

urlpatterns = [
    path('', views.redirect_to_signup, name='root'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('change-password/', views.change_password_view, name='change_password'),

    path('welcome-dashboard/', views.welcome_dashboard, name='welcome_dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('download-summary/', views.download_summary, name='download_summary'),

    path('trip-generator/', views.trip_generator, name='trip_generator'),
    path('trip-closure/', views.trip_closure, name='trip_closure'),

    path('trip-audit/', views.trip_audit_dashboard, name='trip_audit'),
    path('audit/<str:trip_id>/', views.audit_trip, name='audit_trip'),

    path('financial-dashboard/', views.financial_dashboard, name='financial_dashboard'),
    path('user-settings/', views.user_settings, name='user_settings'),
]
