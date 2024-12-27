from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib.auth import (
    authenticate,
    login as auth_login,
    logout,
    get_user_model,
)
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from mainapps.accounts.emails import send_html_email2
from django.conf import settings
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from .models import Plan, Subscription, StripeCustomer
import uuid

def logout_view(request):
    logout(request)

    messages.success(request, "You Have Been Successfully Logged Out.")

    return redirect("/")


def login(request):
    if request.user.is_authenticated:
        return redirect("/")

    if request.method == "POST":
        email = request.POST["email"]
        password = request.POST["password"]

        user = authenticate(request, username=email, password=password)

        if user is not None:
            if user.verification_token is None:
                auth_login(request, user)

                try:
                    return redirect(request.session.get("next"))
                except:
                    return redirect("/")
            else:
                messages.error(
                    request,
                    "Your Email Address Is Not Verified. Please Verify Your Email Before Logging In.",
                )
        else:
            messages.error(request, "Invalid Username or Password. Please Try Again.")

    next = request.GET.get("next", "")
    request.session["next"] = next
    return render(
        request,
        "accounts/login.html",
    )


def register(request):
    verification=None
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        password1 = request.POST.get("password")
        password2 = request.POST.get("Confirmpassword")

        if len(password1) < 6:
            messages.error(request, "At Least 6 Characters Are Required")
            return render(
                request,
                "/accounts/signup.html",
            )

        if password1 != password2:
            messages.error(request, "Passwords Do Not Match.")
            return render(
                request,
                "/accounts/signup.html",
                
            )

        User = get_user_model()
        if User.objects.filter(email=email).exists():
            messages.error(request, "This Email Is Already Registered.")
            return render(
                request,
                "accounts/signup.html",
                {'verification':verification}
            )

        user = User.objects.create_user(email=email, password=password1)
        user.first_name = name
        user.save()
    
        verification_token = str(uuid.uuid4())
        user.verification_token = verification_token

        send_html_email2(
            subject="Welcome to LernOn.io – Verify Your Email To Continue",
            message=None,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to_email=user.email,
            html_file="accounts/verification.html",
            context={
                "first_name": user.first_name,
                "verification_url": settings.DOMAIN_NAME
                + reverse("accounts:verify", kwargs={"token": verification_token}),
            },
        )
        return redirect('/')
    else:
        return render(
            request,
            "/accounts/signup.html",
            {"verification":verification}
        )


def verify(request, token):
    try:
        user = get_user_model().objects.get(verification_token=token)

        if user is not None:
            user.verification_token = None
            user.save()

            auth_login(request, user)
            return redirect("/accounts/")
    except:
        return redirect(reverse("home:home"))

