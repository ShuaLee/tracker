from django.urls import path

from . import views

urlpatterns = [
    path("csrf/", views.CsrfCookieView.as_view(), name="auth-csrf"),
    path("register/", views.RegisterView.as_view(), name="auth-register"),
    path("verify-email/", views.VerifyEmailView.as_view(), name="auth-verify-email"),
    path(
        "resend-verification/",
        views.ResendVerificationView.as_view(),
        name="auth-resend-verification",
    ),
    path("login/", views.LoginView.as_view(), name="auth-login"),
    path("logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("logout-all/", views.LogoutAllView.as_view(), name="auth-logout-all"),
    path("me/", views.MeView.as_view(), name="auth-me"),
    path("options/", views.OptionsView.as_view(), name="auth-options"),
    path("security-events/", views.SecurityEventsView.as_view(), name="auth-security-events"),
    path(
        "password/change/",
        views.ChangePasswordView.as_view(),
        name="auth-password-change",
    ),
    path(
        "password/reset/",
        views.PasswordResetRequestView.as_view(),
        name="auth-password-reset",
    ),
    path(
        "password/reset/confirm/",
        views.PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),
    path("email/change/", views.EmailChangeView.as_view(), name="auth-email-change"),
    path("deactivate/", views.DeactivateView.as_view(), name="auth-deactivate"),
]
