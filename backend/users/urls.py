from django.urls import path

from . import views

app_name = "users"

urlpatterns = [
    path("csrf/", views.CsrfView.as_view(), name="csrf"),
    # Registration and email verification
    path("register/", views.RegisterView.as_view(), name="register"),
    path("verify-email/", views.VerifyEmailView.as_view(), name="verify-email"),
    path("resend-verification/", views.ResendVerificationView.as_view(), name="resend-verification"),
    # Sessions
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("logout-all/", views.LogoutAllView.as_view(), name="logout-all"),
    # The signed-in user
    path("me/", views.MeView.as_view(), name="me"),
    path("options/", views.OptionsView.as_view(), name="options"),
    path("security-events/", views.SecurityEventsView.as_view(), name="security-events"),
    # Password
    path("password/change/", views.ChangePasswordView.as_view(), name="password-change"),
    path("password/reset/", views.PasswordResetView.as_view(), name="password-reset"),
    path("password/reset/confirm/", views.PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    # Email and account
    path("email/change/", views.ChangeEmailView.as_view(), name="email-change"),
    path("delete-account/", views.DeleteAccountView.as_view(), name="delete-account"),
]
