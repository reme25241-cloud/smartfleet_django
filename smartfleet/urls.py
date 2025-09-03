from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from fleet import views

urlpatterns = [
    # Authentication
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("change-password/", views.change_password, name="change_password"),

    # Forgot Password (Password Reset Flow)
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset.html"
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),

    # Admin
    path("admin/", admin.site.urls),

    # Dashboards
    path("", views.index, name="index"),
    path("welcome-dashboard/", views.welcome_dashboard, name="welcome_dashboard"),
    path("fleet-dashboard/", views.fleet_dashboard_redirect, name="fleet_dashboard_redirect"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("financial-dashboard/", views.financial_dashboard, name="financial_dashboard"),

    # User management
    path("user-settings/", views.user_settings, name="user_settings"),
    path("add_user/", views.add_user, name="add_user"),
    path("update_rights/", views.update_rights, name="update_rights"),

    # Trip management
    path("trip-generator/", views.trip_generator, name="trip_generator"),
    path("trip-closure/", views.trip_closure, name="trip_closure"),
    path("trip-audit/", views.trip_audit_dashboard, name="trip_audit_dashboard"),
    path("audit/<str:trip_id>/", views.audit_trip, name="audit_trip"),
    path("download-summary/", views.download_summary, name="download_summary"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
