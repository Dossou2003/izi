from django.shortcuts import render

# Create your views here.

from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail

from django.shortcuts import render, redirect
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator

from .utils import get_leaderboard 


from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect


from django.contrib.auth.decorators import login_required



User = get_user_model()
# ===============================Enregistrement d'utilisateur=======================

def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        user = User.objects.create_user(username=username, email=email, password=password)
        user.is_active = False  # Désactiver l'utilisateur jusqu'à l'activation par email
        user.save()

        # Envoyer un email d'activation
        current_site = get_current_site(request)
        mail_subject = 'Activez votre compte.'
        message = render_to_string('account_activation_email.html', {
            'user': user,
            'domain': current_site.domain,
            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
            'token': default_token_generator.make_token(user),
        })
        send_mail(mail_subject, message, 'from@example.com', [user.email])

        return render(request, 'registration/registration_complete.html', {
            'message': "Un email d'activation a été envoyé à votre adresse email."
        })
    return render(request, 'registration/register.html')


# ===========================================Activation de compte=================================

def activate_account(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        return render(request, 'registration/activation_complete.html', {
            'message': "Votre compte a été activé avec succès."
        })
    else:
        return render(request, 'registration/activation_failed.html', {
            'error': "Lien d'activation invalide."
        })


# =========================================================Connexion utilisateur=========================
def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            if user.is_active:
                login(request, user)
                return redirect('home')
            else:
                return render(request, 'registration/login.html', {
                    'error': "Votre compte n'est pas encore activé."
                })
        else:
            return render(request, 'registration/login.html', {
                'error': "Identifiant ou mot de passe incorrect."
            })
    return render(request, 'registration/login.html')



# ======================================================== Affichage des détails de l'utilisateur====================================




@login_required
def user_details(request):
    return render(request, 'user/details.html', {
        'user': request.user
    })

# =========================================Classement des utilisateurs=====================
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required
def leaderboard(request):
    leaderboard_data = get_leaderboard()
    return render(request, 'user/leaderboard.html', {
        'leaderboard': leaderboard_data
    })