

# Create your views here.
from django.shortcuts import render, get_object_or_404
from .serializers import CartItemSerializer
from rest_framework import viewsets, permissions, parsers

from rest_framework import viewsets, permissions, status, filters, serializers
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.authtoken.models import  Token
from .models import PointProgress, Room, ChatMessage
from .serializers import RoomSerializer, MessageSerializer
from django.http import JsonResponse

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
import fedapay

from .models import Cart, CartItem, Product
from .serializers import CartSerializer, CartItemSerializer

#from .chatbot import chat  




from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .models import Conversation, ConversationMessage, ReferenceDocument
from .serializers import ConversationSerializer, ConversationMessageSerializer, ReferenceDocumentSerializer


from  django.contrib.auth import authenticate, login

from django.contrib.auth.models import AnonymousUser
from django.shortcuts import get_object_or_404

from django.db.models import Sum  

from django.db.models.functions import TruncMonth  
  # Pour regrouper par mois

from rest_framework.pagination import PageNumberPagination
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi  

import secrets
from django.conf import settings
from .models import *
from .serializers import *
from .permissions import IsMentor, IsLearner


from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Avg, F, Window
from django.db.models import Q 
from django.contrib.auth import get_user_model
import logging
from bourjon import models

User = get_user_model()
logger = logging.getLogger(__name__)

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100



class UserDetailsSerializer(serializers.ModelSerializer):
    """
    Sérialiseur pour afficher les détails complets d'un utilisateur, y compris les informations 
    spécifiques à son rôle (apprenant ou mentor).
    """
    learner_details = LearnerSerializer(source='learner', read_only=True)  # Détails du profil d'apprenant (si l'utilisateur est un apprenant)
    mentor_details = MentorSerializer(source='mentor', read_only=True)  # Détails du profil de mentor (si l'utilisateur est un mentor)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'status', 'image', 'points', 'learner_details', 'mentor_details']



from django.contrib.auth import get_user_model, authenticate, login
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status
from .tokens import account_activation_token
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from .utils import get_leaderboard 
from rest_framework_simplejwt.tokens import RefreshToken


User = get_user_model()


class ActivateAccountView(APIView):
    """
    View to activate a user's account using an activation token.
    """

    def get(self, request, *args, **kwargs):
        uidb64 = kwargs.get('uidb64')  # Récupérer uidb64 depuis les paramètres d'URL
        token = kwargs.get('token')    # Récupérer token depuis les paramètres d'URL

        if not uidb64 or not token:
            return Response(
                {"error": "UID and token are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = get_user_model().objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, get_user_model().DoesNotExist):
            return Response(
                {"error": "Invalid activation link."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if default_token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            return Response({
                "message": "Account activated successfully.",
            }, status=status.HTTP_200_OK)
        else:
            return Response(
                {"error": "Invalid token."},
                status=status.HTTP_400_BAD_REQUEST
            )



class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    pagination_class = StandardResultsSetPagination

    def get_permissions(self):
        if self.action in ['register', 'login', 'get_user_id', 'activate_account', 'password_reset_confirm']:
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        user = get_object_or_404(User, pk=pk)
        messages = Message.objects.filter(Q(sender=user) | Q(recipient=user))
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def register(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user.is_active = False
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

            return Response({'message': 'Un email d\'activation a été envoyé à votre adresse email.'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def login(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            if user.is_active:
                login(request, user)
                return Response({'message': f"Bienvenue {user.first_name} !"}, status=status.HTTP_200_OK)
            else:
                return Response({'message': "Votre compte n'est pas encore activé."}, status=status.HTTP_401_UNAUTHORIZED)
        return Response({'message': "Identifiant ou mot de passe incorrect."}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def leaderboard(self, request):
        leaderboard = get_leaderboard()
        serializer = UserSerializer(leaderboard, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['put'], parser_classes=[parsers.MultiPartParser])
    def set_profile_picture(self, request, pk=None):
        user = self.get_object()
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my_details(self, request):
        serializer = UserDetailsSerializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny], url_path='get-id')
    def get_user_id(self, request):
        username = request.query_params.get('username')
        if not username:
            return Response({'error': 'Veuillez fournir un nom d\'utilisateur.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = get_object_or_404(User, username=username)
            return Response({"user_id": user.id}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "Utilisateur non trouvé."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny], url_path='activate/<uidb64>/<token>')
    def activate_account(self, request, uidb64=None, token=None):
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            return Response({'status': 'Account activated successfully'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid token or user'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny], url_path='reset-password/<uidb64>/<token>')
    def password_reset_confirm(self, request, uidb64=None, token=None):
        new_password = request.data.get('new_password')
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            user.set_password(new_password)
            user.save()
            return Response({'status': 'Password reset successfully'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid token or user'}, status=status.HTTP_400_BAD_REQUEST)



class UserCustomIDSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'custom_id']




# ViewSet pour récupérer le classement des utilisateurs
class LeaderboardViewSet(viewsets.ViewSet):
    """
    ViewSet pour récupérer le classement des utilisateurs.
    """
    permission_classes = [IsAuthenticated]  # Ou IsAuthenticated si vous voulez restreindre l'accès

    def list(self, request):
        """
        Récupère le classement des utilisateurs.
        """
        logger.info(f"Utilisateur {request.user.username} a demandé le classement.")  # Log de la requête utilisateur
        
        leaderboard = get_leaderboard()  # Appel à la fonction pour récupérer le classement
        serializer = UserCustomIDSerializer(leaderboard, many=True)
        
        logger.debug(f"Classement des utilisateurs: {serializer.data}")  # Log des données du classement
        return Response(serializer.data)









class SessionViewSet(viewsets.ModelViewSet):
    queryset = Session.objects.all()
    serializer_class = SessionSerializer  
    pagination_class = StandardResultsSetPagination

    def get_permissions(self):
        logger.info(f"User {self.request.user.id} attempting to perform {self.action} on Session")
        if self.action == 'create':
            permission_classes = [IsLearner]
        elif self.action in ['start_session', 'end_session']:
            permission_classes = [IsMentor]
        elif self.action == 'video_chat':
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        logger.info(f"User {self.request.user.id} creating a new session")
        serializer.save(learner=self.request.user.learner)

    @action(detail=True, methods=['post'])
    def video_chat(self, request, pk=None):
        session = self.get_object()
        logger.info(f"User {request.user.id} attempting to start video chat for session {session.id}")
        if hasattr(session, 'video_chat'):
            video_chat = session.video_chat
        else:
            video_chat = VideoChat.objects.create(session=session)
        jitsi_domain = settings.JITSI_DOMAIN
        room_name = f"session_{session.id}_{session.learner.user.username.replace(' ', '_')}"
        password = secrets.token_urlsafe(10)
        video_chat_url = f"https://{jitsi_domain}/{room_name}#config.roomPassword={password}"
        video_chat.video_chat_url = video_chat_url
        video_chat.save()
        logger.info(f"Video chat started for session {session.id} by User {request.user.id}")
        return Response({
            'video_chat_url': video_chat_url,
            'room_name': room_name,
            'password': password
        })

    @action(detail=True, methods=['post'])
    def start_session(self, request, pk=None):
        session = self.get_object()
        if session.status_session == 'planifiée':
            session.status_session = 'en cours'
            session.save()
            logger.info(f"Session {session.id} started by User {request.user.id}")
            return Response({'message': 'Session démarrée'}, status=status.HTTP_200_OK)
        logger.warning(f"Failed to start session {session.id} by User {request.user.id}")
        return Response({'message': 'La session ne peut pas être démarrée'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def end_session(self, request, pk=None):
        session = self.get_object()
        if session.status_session == 'en cours':
            session.status_session = 'terminée'
            session.save()
            logger.info(f"Session {session.id} ended by User {request.user.id}")
            return Response({'message': 'Session terminée'}, status=status.HTTP_200_OK)
        logger.warning(f"Failed to end session {session.id} by User {request.user.id}")
        return Response({'message': 'La session ne peut pas être terminée'}, status=status.HTTP_400_BAD_REQUEST)

class MentorViewSet(viewsets.ModelViewSet):
    queryset = Mentor.objects.all()
    serializer_class = MentorSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]  
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]  
    search_fields = ['user__username', 'specialty']




class LearnerViewSet(viewsets.ModelViewSet):
    queryset = Learner.objects.all()
    serializer_class = LearnerSerializer
    permission_classes = [permissions.IsAdminUser] 
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['user__username']

    @action(detail=True, methods=['get'])
    def courses(self, request, pk=None):
        """
        Récupère les cours suivis par l'apprenant.
        """
        learner = self.get_object()
        logger.info(f"Utilisateur {learner.user.username} a demandé les cours suivis.")
        
        courses_taken = Course.objects.filter(activity__user=learner.user, activity__activity_type='étude').distinct()
        serializer = CourseSerializer(courses_taken, many=True)
        
        logger.debug(f"Cours suivis par {learner.user.username}: {serializer.data}")
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def hours_spent(self, request, pk=None):
        """
        Récupère les heures passées en étude et en examen par l'apprenant, éventuellement filtrées par mois.
        """
        learner = self.get_object()
        logger.info(f"Utilisateur {learner.user.username} a demandé les heures passées.")

        queryset = Activity.objects.filter(user=learner.user)
        if 'month' in request.query_params:
            queryset = queryset.annotate(month=TruncMonth('start_time')).values('month').annotate(total_duration=Sum('duration'))
        else:
            queryset = queryset.values('activity_type').annotate(total_duration=Sum('duration'))

        for item in queryset:
            item['total_duration_hours'] = item['total_duration'].total_seconds() / 3600

        serializer = ActivitySerializer(queryset, many=True)
        
        logger.debug(f"Heures passées par {learner.user.username}: {serializer.data}")
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def grades(self, request, pk=None):
        """
        Récupère les notes obtenues par l'apprenant.
        """
        learner = self.get_object()
        logger.info(f"Utilisateur {learner.user.username} a demandé ses notes.")

        grades = learner.grades.all()
        serializer = GradeSerializer(grades, many=True)
        
        logger.debug(f"Notes obtenues par {learner.user.username}: {serializer.data}")
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def tasks(self, request, pk=None):
        """
        Récupère les tâches de l'apprenant.
        """
        learner = self.get_object()
        logger.info(f"Utilisateur {learner.user.username} a demandé ses tâches.")

        tasks = learner.user.task_set.all()
        serializer = TaskSerializer(tasks, many=True)
        
        logger.debug(f"Tâches de {learner.user.username}: {serializer.data}")
        return Response(serializer.data)



class PaymentServiceViewSet(viewsets.ModelViewSet):
    queryset = PaymentService.objects.all()
    serializer_class = PaymentServiceSerializer
    permission_classes = [IsAuthenticated]  # Les utilisateurs authentifiés peuvent gérer leurs paiements
    pagination_class = StandardResultsSetPagination

    def perform_create(self, serializer):
        """
        Validation pour vérifier si le learner a déjà un paiement en cours pour le même service_type.
        """
        learner = self.request.user.learner
        service_type = serializer.validated_data['service_type']
        logger.info(f"Utilisateur {self.request.user.username} tente de créer un paiement pour le service {service_type}.")
        
        if PaymentService.objects.filter(learner=learner, service_type=service_type, status_session__in=['planifiée', 'en cours']).exists():
            logger.warning(f"Utilisateur {self.request.user.username} a déjà un paiement en cours pour le service {service_type}.")
            raise serializers.ValidationError("Vous avez déjà un paiement en cours pour ce type de service.")

        logger.info(f"Création du paiement pour l'utilisateur {self.request.user.username} et le service {service_type}.")
        serializer.save(learner=learner)

    def create(self, request, *args, **kwargs):
        """
        Création d'un paiement avec validation de paiement en cours.
        """
        logger.info(f"Demande de création de paiement reçue pour l'utilisateur {request.user.username}.")
        response = super().create(request, *args, **kwargs)
        logger.info(f"Création de paiement pour l'utilisateur {request.user.username} complétée avec succès.")
        return response





class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = StandardResultsSetPagination


class SubCategoryViewSet(viewsets.ModelViewSet):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = StandardResultsSetPagination

    # Filtrage par catégorie
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category']





class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = StandardResultsSetPagination

    # Filtrage par sous-catégorie et niveau de difficulté
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['sub_category', 'difficulty_level']

    def list(self, request, *args, **kwargs):
        """
        Liste les cours avec filtrage et pagination.
        """
        logger.info(f"Demande de liste des cours reçue de la part de l'utilisateur {request.user.username}.")
        response = super().list(request, *args, **kwargs)
        logger.info(f"Liste des cours envoyée à l'utilisateur {request.user.username}.")
        return response

    def retrieve(self, request, *args, **kwargs):
        """
        Récupère les détails d'un cours spécifique.
        """
        logger.info(f"Demande de détails pour le cours ID {kwargs.get('pk')} reçue de la part de l'utilisateur {request.user.username}.")
        response = super().retrieve(request, *args, **kwargs)
        logger.info(f"Détails du cours ID {kwargs.get('pk')} envoyés à l'utilisateur {request.user.username}.")
        return response

    @action(detail=True, methods=['get'])
    def enrollment_count(self, request, pk=None):
        """
        Récupère le nombre d'inscrits à un cours.
        """
        course = self.get_object()
        count = course.activity_set.filter(activity_type='étude').count()
        logger.info(f"Demande du nombre d'inscrits pour le cours ID {pk} reçue de la part de l'utilisateur {request.user.username}.")
        logger.info(f"Nombre d'inscrits pour le cours ID {pk} : {count}.")
        return Response({'enrollment_count': count})

    
    
    
class ResourceViewSet(viewsets.ModelViewSet):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = StandardResultsSetPagination






class RatingViewSet(viewsets.ModelViewSet):
    queryset = Rating.objects.all()
    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def perform_create(self, serializer):
        """
        Sauvegarde la note avec l'utilisateur courant comme auteur et met à jour la note moyenne du mentor.
        """
        # Sauvegarde de la note
        serializer.save(user=self.request.user)
        # Mise à jour de la note moyenne du mentor
        mentor = serializer.instance.mentor
        mentor.update_average_rating()

        # Log de la création de la note
        logger.info(f"Note créée par l'utilisateur {self.request.user.username} pour le mentor {mentor.username}.")
        logger.info(f"La note moyenne du mentor {mentor.username} a été mise à jour.")

    def create(self, request, *args, **kwargs):
        """
        Gère la création d'une nouvelle note et enregistre le log associé.
        """
        logger.info(f"Demande de création d'une note reçue de la part de l'utilisateur {request.user.username}.")
        response = super().create(request, *args, **kwargs)
        logger.info(f"Note créée et enregistrée pour l'utilisateur {request.user.username}.")
        return response







class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]  

    def perform_create(self, serializer):
        """
        Sauvegarde la tâche en associant l'utilisateur courant.
        """
        serializer.save(user=self.request.user)
        logger.info(f"Tâche créée : {serializer.instance}. Associée à l'utilisateur {self.request.user.username}.")

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """
        Marque la tâche comme terminée si l'utilisateur est autorisé.
        """
        task = self.get_object()
        if task.user == request.user:
            task.is_completed = True
            task.save()
            logger.info(f"Tâche {task.id} marquée comme terminée par l'utilisateur {request.user.username}.")
            return Response({'message': 'Tâche marquée comme terminée'}, status=status.HTTP_200_OK)
        logger.warning(f"Tentative d'accès non autorisé pour la tâche {task.id} par l'utilisateur {request.user.username}.")
        return Response({'message': 'Vous n\'êtes pas autorisé à modifier cette tâche'}, status=status.HTTP_403_FORBIDDEN)


    
    
    def get_leaderboard():
        """
        Récupère le classement des utilisateurs basé sur leurs points.
        """
        leaderboard = User.objects.order_by('-points').annotate(
            rank=models.Window(
                expression=models.F('row_number'),
                order_by=models.F('points').desc(),
            )
        )
        logger.info(f"Classement des utilisateurs récupéré avec {leaderboard.count()} utilisateurs.")
        return leaderboard

    @receiver(post_save, sender=Activity)
    def update_user_points(sender, instance, created, **kwargs):
        """
        Met à jour les points de l'utilisateur après la création d'une activité.
        """
        if created:
            if instance.activity_type == 'étude':
                points_to_add = int(instance.duration.total_seconds() / 60)  # 1 point par minute d'étude
            elif instance.activity_type == 'examen':
                points_to_add = 100  # 100 points par examen réussi (à adapter)
            else:
                points_to_add = 0  # Autres types d'activités

            instance.user.points += points_to_add
            instance.user.save()
            logger.info(f"Points ajoutés pour l'utilisateur {instance.user.username}. Points supplémentaires : {points_to_add}. Total des points : {instance.user.points}.")



      

class PaymentServiceViewSet(viewsets.ModelViewSet):
    queryset = PaymentService.objects.all()
    serializer_class = PaymentServiceSerializer
    permission_classes = [IsAuthenticated]  # Les utilisateurs authentifiés peuvent gérer leurs paiements
    pagination_class = StandardResultsSetPagination

    def perform_create(self, serializer):
        """
        Valide et sauvegarde un paiement, en vérifiant s'il existe déjà un paiement en cours pour le même type de service.
        """
        # Vérification de paiement en cours pour le même type de service
        if PaymentService.objects.filter(
            learner=self.request.user.learner,
            service_type=serializer.validated_data['service_type'],
            status_session__in=['planifiée', 'en cours']
        ).exists():
            logger.warning(f"Tentative de création d'un paiement en double pour le service {serializer.validated_data['service_type']} par l'apprenant {self.request.user.username}.")
            raise serializers.ValidationError("Vous avez déjà un paiement en cours pour ce type de service.")

        # Sauvegarde du paiement
        serializer.save(learner=self.request.user.learner)
        logger.info(f"Paiement créé : {serializer.instance}. Associé à l'apprenant {self.request.user.username}.")




class ActivityViewSet(viewsets.ModelViewSet):
    queryset = Activity.objects.all()
    serializer_class = ActivitySerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        """
        Sauvegarde une nouvelle activité associée à l'utilisateur authentifié et enregistre un log.
        """
        serializer.save(user=self.request.user)
        logger.info(f"Activité créée : {serializer.instance}. Associée à l'utilisateur {self.request.user.username}.")




class VideoChatViewSet(viewsets.ModelViewSet):  

    queryset = VideoChat.objects.all()
    serializer_class = VideoChatSerializer
    permission_classes = [IsAuthenticated]




class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        logger.info(f"User {self.request.user.id} is creating an assignment.")
        serializer.save(created_by=self.request.user)

    def get_queryset(self):
        if self.request.user.is_staff:
            return Assignment.objects.all()
        else:
            return Assignment.objects.filter(learner=self.request.user.learner)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        logger.info(f"Assignment created successfully by user {request.user.id}.")
        return response

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        logger.info(f"Assignment updated successfully by user {request.user.id}.")
        return response

    def destroy(self, request, *args, **kwargs):
        response = super().destroy(request, *args, **kwargs)
        logger.info(f"Assignment deleted successfully by user {request.user.id}.")
        return response
    
    



class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        logger.info(f"User {self.request.user.id} is creating a report.")
        serializer.save(learner=self.request.user.learner)

    def get_queryset(self):
        return Report.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        logger.info(f"Report created successfully by user {request.user.id}.")
        return response

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        logger.info(f"Report updated successfully by user {request.user.id}.")
        return response

    def destroy(self, request, *args, **kwargs):
        response = super().destroy(request, *args, **kwargs)
        logger.info(f"Report deleted successfully by user {request.user.id}.")
        return response





class FileViewSet(viewsets.ModelViewSet):
    queryset = File.objects.all()
    serializer_class = FileSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def perform_create(self, serializer):
        logger.info(f"User {self.request.user.id} is uploading a file.")
        serializer.save(uploaded_by=self.request.user)

    def get_queryset(self):
        return File.objects.filter(Q(uploaded_by=self.request.user) |
                                   Q(course__in=self.request.user.learner.courses.all()))

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        logger.info(f"File uploaded successfully by user {request.user.id}.")
        return response

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        logger.info(f"File updated successfully by user {request.user.id}.")
        return response

    def destroy(self, request, *args, **kwargs):
        response = super().destroy(request, *args, **kwargs)
        logger.info(f"File deleted successfully by user {request.user.id}.")
        return response



class ChatMessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def perform_create(self, serializer):
        logger.info(f"User {self.request.user.id} is creating a new chat message.")
        serializer.save(sender=self.request.user)

    def get_queryset(self):
        return Message.objects.filter(Q(sender=self.request.user) | Q(recipient=self.request.user))

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        logger.info(f"Chat message created successfully by user {request.user.id}.")
        return response

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        logger.info(f"Chat message updated successfully by user {request.user.id}.")
        return response

    def destroy(self, request, *args, **kwargs):
        response = super().destroy(request, *args, **kwargs)
        logger.info(f"Chat message deleted successfully by user {request.user.id}.")
        return response

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        message = self.get_object()
        if message.recipient == request.user:
            message.is_read = True
            message.save()
            logger.info(f"User {request.user.id} marked message {message.id} as read.")
            return Response({'message': 'Message marked as read'}, status=status.HTTP_200_OK)
        return Response({'message': 'You are not authorized to modify this message'}, status=status.HTTP_403_FORBIDDEN)


    

class MentorProfileViewSet(viewsets.ModelViewSet):
    queryset = MentorProfile.objects.all()
    serializer_class = MentorProfileSerializer
    permission_classes  = [IsAuthenticated]  # Ou ajustez les permissions selon vos besoins

    def perform_create(self, serializer):
        serializer.save(mentor=self.request.user.mentor)

class EnrollmentViewSet(viewsets.ModelViewSet):
    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentSerializer
    permission_classes  = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(learner=self.request.user.learner)



# =======================pour le chat de discussion==========

class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        logger.info(f"User {request.user.id} retrieved rooms list.")
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        logger.info(f"User {request.user.id} is creating a new room.")
        response = super().create(request, *args, **kwargs)
        if response.status_code == status.HTTP_201_CREATED:
            logger.info(f"Room created successfully by user {request.user.id}.")
        else:
            logger.error(f"Failed to create room by user {request.user.id}.")
        return response

    def retrieve(self, request, *args, **kwargs):
        logger.info(f"User {request.user.id} is retrieving a room.")
        return super().retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        logger.info(f"User {request.user.id} is updating a room.")
        response = super().update(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            logger.info(f"Room updated successfully by user {request.user.id}.")
        else:
            logger.error(f"Failed to update room by user {request.user.id}.")
        return response

    def destroy(self, request, *args, **kwargs):
        logger.info(f"User {request.user.id} is deleting a room.")
        response = super().destroy(request, *args, **kwargs)
        if response.status_code == status.HTTP_204_NO_CONTENT:
            logger.info(f"Room deleted successfully by user {request.user.id}.")
        else:
            logger.error(f"Failed to delete room by user {request.user.id}.")
        return response
 
 
   


class ChatMessageViewSet(viewsets.ModelViewSet):
    queryset = ChatMessage.objects.all()
    serializer_class = ChatMessageSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        logger.info(f"User {request.user.id} retrieved chat messages list.")
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        logger.info(f"User {request.user.id} is creating a new chat message.")
        response = super().create(request, *args, **kwargs)
        if response.status_code == status.HTTP_201_CREATED:
            logger.info(f"Chat message created successfully by user {request.user.id}.")
        else:
            logger.error(f"Failed to create chat message by user {request.user.id}.")
        return response

    def retrieve(self, request, *args, **kwargs):
        logger.info(f"User {request.user.id} is retrieving a chat message.")
        return super().retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        logger.info(f"User {request.user.id} is updating a chat message.")
        response = super().update(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            logger.info(f"Chat message updated successfully by user {request.user.id}.")
        else:
            logger.error(f"Failed to update chat message by user {request.user.id}.")
        return response

    def destroy(self, request, *args, **kwargs):
        logger.info(f"User {request.user.id} is deleting a chat message.")
        response = super().destroy(request, *args, **kwargs)
        if response.status_code == status.HTTP_204_NO_CONTENT:
            logger.info(f"Chat message deleted successfully by user {request.user.id}.")
        else:
            logger.error(f"Failed to delete chat message by user {request.user.id}.")
        return response
    



class CartViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CartItemSerializer

    def get_queryset(self):
        return CartItem.objects.filter(user=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        cart_items = self.get_queryset()
        serializer = self.get_serializer(cart_items, many=True)
        logger.info(f"User {request.user.id} retrieved their cart items.")
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_item(self, request, *args, **kwargs):
        course_id = request.data.get('course_id')
        quantity = request.data.get('quantity', 1)
        course = get_object_or_404(Course, id=course_id)
        cart_item, created = CartItem.objects.get_or_create(user=request.user, course=course)

        if not created:
            cart_item.quantity += quantity
        else:
            cart_item.quantity = quantity

        cart_item.save()
        logger.info(f"User {request.user.id} added item {course_id} to cart.")
        return Response({"message": "Item added to cart"})

    @action(detail=True, methods=['delete'])
    def remove_item(self, request, pk=None):
        cart_item = self.get_object()
        cart_item.delete()
        logger.info(f"User {request.user.id} removed item {pk} from cart.")
        return Response({"message": "Course removed from cart"})

    @action(detail=False, methods=['get'])
    def my_cart(self, request):
        cart_items = self.get_queryset()
        serializer = self.get_serializer(cart_items, many=True)
        logger.info(f"User {request.user.id} retrieved their cart content.")
        return Response(serializer.data)
    
    
    



class FedaPayCheckoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cart = Cart.objects.get(user=request.user)
        total_amount = sum(item.product.price * item.quantity for item in cart.items.all())

        fedapay.api_key = 'YOUR_FEDAPAY_API_KEY'
        try:
            transaction = fedapay.Transaction.create({
                'amount': total_amount,
                'description': 'Payment for cart items',
                'currency': {'iso': 'XOF'},
                'callback_url': 'YOUR_CALLBACK_URL',
                'customer': {
                    'firstname': request.user.first_name,
                    'lastname': request.user.last_name,
                    'email': request.user.email,
                    'phone_number': request.user.phone_number,
                },
            })
            logger.info(f"User {request.user.id} initiated FedaPay checkout.")
            return Response({'checkout_url': transaction.checkout_url})
        except Exception as e:
            logger.error(f"Failed to initiate FedaPay checkout for user {request.user.id}: {str(e)}")
            return Response({'error': 'An error occurred during payment initiation.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




from .serializers import PointProgressSerializer

class PointProgressViewSet(viewsets.ModelViewSet):
    queryset = PointProgress.objects.all()
    serializer_class = PointProgressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PointProgress.objects.filter(learner=self.request.user.learner)

    
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        logger.info(f"User {request.user.id} created point progress entry.")
        return response

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        logger.info(f"User {request.user.id} updated point progress entry.")
        return response

    def destroy(self, request, *args, **kwargs):
        response = super().destroy(request, *args, **kwargs)
        logger.info(f"User {request.user.id} deleted point progress entry.")
        return response



class RAGViewSet(viewsets.ViewSet):

    def create(self, request):
        question = request.data.get('question')
        if not question:
            logger.warning(f"User {request.user.id} failed to provide a question.")
            return Response({'error': 'Veuillez fournir une question.'}, status=status.HTTP_400_BAD_REQUEST)

        # Create or get the user's conversation
        conversation, created = Conversation.objects.get_or_create(user=request.user)

        try:
            reference_documents = ReferenceDocument.objects.all()
            answer = chat(question, reference_documents)

            # Save the question and answer to conversation history
            ConversationMessage.objects.create(conversation=conversation, sender='user', content=question)
            ConversationMessage.objects.create(conversation=conversation, sender='rag', content=answer)

            logger.info(f"User {request.user.id} asked a question and received an answer.")
            return Response({'answer': answer})
        except Exception as e:
            logger.error(f"Error processing request from user {request.user.id}: {str(e)}")
            return Response({'error': 'Une erreur est survenue lors du traitement de votre requête.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class ConversationViewSet(viewsets.ModelViewSet):
    queryset = Conversation.objects.all()
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        logger.info(f"User {request.user.id} created a new conversation.")
        return response

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        logger.info(f"User {request.user.id} updated a conversation.")
        return response

    def destroy(self, request, *args, **kwargs):
        response = super().destroy(request, *args, **kwargs)
        logger.info(f"User {request.user.id} deleted a conversation.")
        return response
    
    
       
class ConversationMessageViewSet(viewsets.ModelViewSet):
    queryset = ConversationMessage.objects.all()
    serializer_class = ConversationMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        conversation_id = self.kwargs.get('conversation_pk')
        return ConversationMessage.objects.filter(conversation_id=conversation_id)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        logger.info(f"User {request.user.id} sent a message in conversation {self.kwargs.get('conversation_pk')}.")
        return response

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        logger.info(f"User {request.user.id} updated a message in conversation {self.kwargs.get('conversation_pk')}.")
        return response

    def destroy(self, request, *args, **kwargs):
        response = super().destroy(request, *args, **kwargs)
        logger.info(f"User {request.user.id} deleted a message from conversation {self.kwargs.get('conversation_pk')}.")
        return response
    
    
     

class ReferenceDocumentViewSet(viewsets.ModelViewSet):
    queryset = ReferenceDocument.objects.all()
    serializer_class = ReferenceDocumentSerializer
    permission_classes = [permissions.IsAdminUser]  # Adjust permissions as needed

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        logger.info(f"Admin user {request.user.id} created a new reference document.")
        return response

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        logger.info(f"Admin user {request.user.id} updated a reference document.")
        return response

    def destroy(self, request, *args, **kwargs):
        response = super().destroy(request, *args, **kwargs)
        logger.info(f"Admin user {request.user.id} deleted a reference document.")
        return response




def index(request):
    return render(request, 'index.html')
def dashboard(request):
        return render(request, 'pages/dashboard.html')