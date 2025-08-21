from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from fleet import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('welcome-dashboard/', views.welcome_dashboard, name='welcome_dashboard'),
    path('fleet-dashboard/', views.fleet_dashboard_redirect, name='fleet_dashboard_redirect'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('user-settings/', views.user_settings, name='user_settings'),
    path('add_user/', views.add_user, name='add_user'),
    path('update_rights/', views.update_rights, name='update_rights'),
    path('trip-generator/', views.trip_generator, name='trip_generator'),
    path('trip-closure/', views.trip_closure, name='trip_closure'),
    path('trip-audit/', views.trip_audit_dashboard, name='trip_audit_dashboard'),
    path('audit/<str:trip_id>/', views.audit_trip, name='audit_trip'),
    path('download-summary/', views.download_summary, name='download_summary'),
    path('financial-dashboard/', views.financial_dashboard, name='financial_dashboard'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
