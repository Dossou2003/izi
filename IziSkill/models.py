# Create your models here.

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Avg
from django.utils import timezone
from datetime import datetime, timedelta
from django.conf import settings

class User(AbstractUser):
    """
    Modèle personnalisé pour les utilisateurs, héritant de AbstractUser pour ajouter des champs spécifiques.
    """
    username = models.CharField(max_length=255, verbose_name="Nom d'utilisateur", unique=True)
    password = models.CharField(max_length=255, verbose_name="Mot de passe")
    status = models.CharField(
        max_length=10,
        choices=(
            ('mentor', 'Mentor'),
            ('apprenant', 'Apprenant')
        ),
        verbose_name="Statut")
    image = models.ImageField(upload_to='images/', blank=True, verbose_name="Image de profil")
    email = models.EmailField(unique=True, verbose_name="Adresse e-mail")
    points = models.PositiveIntegerField(default=0, verbose_name="Points")
    custom_id = models.CharField(max_length=255, verbose_name="Identifiant personnalisé", unique=True, blank=True, null=True)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_set',
        blank=True,
        verbose_name="Groupes"
    )

    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_set_permissions',
        blank=True,
        verbose_name="Permissions utilisateur"
    )

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"

    def __str__(self):
        return self.username

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    





class Activity(models.Model):
    """
    Modèle pour suivre les activités des utilisateurs (étude, examens, etc.).
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Utilisateur")
    activity_type = models.CharField(
        max_length=20,
        choices=(
            ('étude', 'Étude'),
            ('examen', 'Examen'),
            # ... autres types d'activités si nécessaire
        ),
        verbose_name="Type d'activité"
    )
    start_time = models.DateTimeField(verbose_name="Heure de début", auto_now_add=True)
    end_time = models.DateTimeField(verbose_name="Heure de fin")
    course = models.ForeignKey('Course', on_delete=models.CASCADE, null=True, blank=True, verbose_name="Cours associé")

    class Meta:
        verbose_name = "Activité"
        verbose_name_plural = "Activités"

    def __str__(self):
        return f"{self.user.username} - {self.activity_type} - {self.start_time} à {self.end_time}"

    @property
    def duration(self):
        """
        Calcule la durée de l'activité.
        """
        if self.end_time:
            return self.end_time - self.start_time
        else:
            return timezone.now() - self.start_time


class Task(models.Model):
    """
    Modèle pour les tâches à faire des utilisateurs.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Utilisateur")
    name = models.CharField(max_length=200, verbose_name="Nom de la tâche")
    course = models.ForeignKey('Course', on_delete=models.CASCADE, null=True, blank=True, verbose_name="Cours associé")
    due_time = models.DateTimeField(verbose_name="Échéance")
    is_completed = models.BooleanField(default=False, verbose_name="Tâche terminée ?")

    class Meta:
        verbose_name = "Tâche"
        verbose_name_plural = "Tâches"

    def __str__(self):
        return self.name

    def clean(self):
        """
        Validation personnalisée pour s'assurer que la date d'échéance est dans le futur.
        """
        if self.due_time <= timezone.now():
            raise ValidationError("La date d'échéance doit être dans le futur.")










class Session(models.Model):
    """
    Modèle pour les sessions de mentorat.
    """
    start_time = models.DateTimeField(verbose_name="Heure de début")
    duration = models.DurationField(verbose_name="Durée")
    pricing = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Prix")
    learner = models.ForeignKey('Learner', on_delete=models.CASCADE, related_name='sessions', verbose_name="Apprenant")
    mentor = models.ForeignKey('Mentor', on_delete=models.SET_NULL, null=True, blank=True, related_name='mentored_sessions', verbose_name="Mentor")
    status_session = models.CharField(
        max_length=20,
        choices=(
            ('planifiée', 'Planifiée'),
            ('en cours', 'En cours'),
            ('terminée', 'Terminée')
        ),
        verbose_name="Statut de la session"
    )
    payment_status = models.CharField(
        max_length=20,
        choices=(
            ('en attente', 'En attente'),
            ('payé', 'Payé'),
            ('remboursé', 'Remboursé')
        ),
        default='en attente',
        verbose_name="Statut du paiement"
    )

    video_chat = models.OneToOneField('VideoChat', on_delete=models.CASCADE, null=True, blank=True, verbose_name="Chat vidéo", related_name='session_video')


    class Meta:
        verbose_name = "Session"
        verbose_name_plural = "Sessions"

    def __str__(self):
        return f"Session {self.id} - {self.learner.user.username} avec {self.mentor.user.username if self.mentor else 'Mentor non affecté'}"










class VideoChat(models.Model):
    """
    Modèle pour stocker des informations sur les sessions de chat vidéo (si nécessaire).
    """
    session = models.OneToOneField(Session, on_delete=models.CASCADE)
    recording_url = models.URLField(blank=True, null=True, verbose_name="URL de l'enregistrement")
    duration = models.DurationField(blank=True, null=True, verbose_name="Durée")

    class Meta:
        verbose_name = "Chat vidéo"
        verbose_name_plural = "Chats vidéo"

    def __str__(self):
        return f"Chat vidéo de la session {self.session.id}"






class Mentor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Utilisateur")
    specialty = models.CharField(max_length=100, verbose_name="Spécialité")
    rate = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Tarif horaire")
    availability = models.CharField(max_length=200, verbose_name="Disponibilités")
    number_courses = models.PositiveIntegerField(default=0, verbose_name="Nombre de cours")
    average_rating = models.FloatField(default=0.0, verbose_name="Note moyenne")
    
    # Champs supplémentaires pour les informations de profil du mentor
    bio = models.TextField(blank=True, verbose_name="Biographie")
    qualifications = models.TextField(blank=True, verbose_name="Qualifications")
    
    
    class Meta:
        verbose_name = "Mentor"
        verbose_name_plural = "Mentors"

    def __str__(self):
        return f"Mentor {self.user.username} - {self.specialty}"

    def update_average_rating(self):
        """
        Met à jour la note moyenne du mentor en fonction des évaluations reçues.
        """
        average_rating = self.ratings.aggregate(Avg('rating'))['rating__avg']
        if average_rating is not None:
            self.average_rating = round(average_rating, 1)  # Arrondir à 1 décimale
            self.save()









class Rating(models.Model):
    """
    Modèle pour les évaluations des mentors.
    """
    mentor = models.ForeignKey(Mentor, on_delete=models.CASCADE, related_name='ratings', verbose_name="Mentor évalué")
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Utilisateur évaluateur")
    rating = models.PositiveIntegerField(verbose_name="Note")
    comment = models.TextField(blank=True, verbose_name="Commentaire")

    class Meta:
        verbose_name = "Évaluation"
        verbose_name_plural = "Évaluations"
        unique_together = ['mentor', 'user']

    def __str__(self):
        return f"Évaluation de {self.mentor} par {self.user} : {self.rating}"

    def clean(self):
        """
        Validation personnalisée pour s'assurer que la note est comprise entre 1 et 5.
        """
        if not 1 <= self.rating <= 5:
            raise ValidationError("La note doit être comprise entre 1 et 5.")

    





class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nom de la catégorie")

    class Meta:
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"

    def __str__(self):
        return self.name





class SubCategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='sub_categories', verbose_name="Catégorie parente")
    name = models.CharField(max_length=100, verbose_name="Nom de la sous-catégorie (Saison)")

    class Meta:
        verbose_name = "Saison"
        verbose_name_plural = "Saisons"

    def __str__(self):
        return f"{self.category.name} - {self.name}"







class Course(models.Model):
    sub_category = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name='courses', verbose_name="Saison")
    title = models.CharField(max_length=200, verbose_name="Titre de l'épisode")
    video = models.FileField(upload_to='course_videos/', verbose_name="Vidéo")
    description = models.TextField(verbose_name="Description")
    duration = models.DurationField(verbose_name="Durée")
    difficulty_level = models.CharField(
        max_length=20,
        choices=(
            ('débutant', 'Débutant'),
            ('intermédiaire', 'Intermédiaire'),
            ('avancé', 'Avancé'),
        ),
        verbose_name="Niveau de difficulté"
    )
    release_date = models.DateField(verbose_name="Date de sortie")
    episode_number = models.PositiveIntegerField(verbose_name="Numéro de l'épisode")
    transcript = models.TextField(blank=True, null=True, verbose_name="Transcription")

    class Meta:
        verbose_name = "Cours"
        verbose_name_plural = "Cours"
        unique_together = ['sub_category', 'episode_number']

    def __str__(self):
        return f"{self.sub_category.name} - Épisode {self.episode_number} : {self.title}"
    
    preview_video = models.URLField(null=True, blank=True)
    thumbnail = models.ImageField(upload_to='thumbnails/', null=True, blank=True)
    instructor = models.ForeignKey('Mentor', on_delete=models.CASCADE, null=True, blank=True)


    
    def __str__(self):
        return self.title





class Resource(models.Model):
    """
    Modèle pour stocker les ressources supplémentaires liées aux cours (PDF, liens externes, etc.).
    """
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='resources', verbose_name="Cours associé")
    name = models.CharField(max_length=200, verbose_name="Nom de la ressource")
    file = models.FileField(upload_to='resources/', null=True, blank=True, verbose_name="Fichier")  # Pour les fichiers PDF, etc.
    link = models.URLField(null=True, blank=True, verbose_name="Lien externe")  # Pour les liens externes
    resource_type = models.CharField(
        max_length=20,
        choices=(
            ('pdf', 'PDF'),
            ('link', 'Lien externe')
        ),
        verbose_name="Type de ressource"
    )

    class Meta:
        verbose_name = "Ressource"
        verbose_name_plural = "Ressources"

    def __str__(self):
        return self.name

    def clean(self):
        """
        Validation personnalisée pour s'assurer qu'un seul type de ressource est défini (fichier ou lien).
        """
        if self.file and self.link:
            raise ValidationError("Vous ne pouvez définir qu'un seul type de ressource : soit un fichier, soit un lien externe.")
        if not self.file and not self.link:
            raise ValidationError("Vous devez définir au moins un type de ressource : soit un fichier, soit un lien externe.")










class Submission(models.Model):
    """
    Modèle pour les soumissions de devoirs par les apprenants.
    """
    assignment = models.ForeignKey('Assignment', on_delete=models.CASCADE, related_name='submissions', verbose_name="Devoir associé")
    learner = models.ForeignKey('Learner', on_delete=models.CASCADE, related_name='submissions', verbose_name="Apprenant")
    file = models.FileField(upload_to='submissions/', verbose_name="Fichier soumis")
    submitted_on = models.DateTimeField(auto_now_add=True, verbose_name="Date de soumission")

    class Meta:
        verbose_name = "Soumission"
        verbose_name_plural = "Soumissions"

    def __str__(self):
        return f"Soumission de {self.learner.user.username} pour {self.assignment.title}"





class Grade(models.Model):
    """
    Modèle pour les notes attribuées aux soumissions de devoirs.
    """
    submission = models.OneToOneField(Submission, on_delete=models.CASCADE, related_name='grade', verbose_name="Soumission associée")
    score = models.PositiveIntegerField(verbose_name="Note")
    feedback = models.TextField(blank=True, verbose_name="Commentaires")

    class Meta:
        verbose_name = "Note"
        verbose_name_plural = "Notes"

    def __str__(self):
        return f"Note {self.score} pour {self.submission.learner.user.username}"






class Learner(models.Model):
    """
    Modèle pour représenter les apprenants.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Utilisateur")
    enrolled_courses = models.ManyToManyField(Course, related_name='enrolled_learners', verbose_name="Cours inscrits", blank=True)
    total_study_time = models.DurationField(default=timedelta(), verbose_name="Temps total d'étude")
    
    # Progression des points de l'apprenant (relation OneToOne avec PointProgress)
    point_progress = models.OneToOneField('PointProgress', on_delete=models.CASCADE, null=True, blank=True, related_name='learner_progress')

    # Objectif de points que l'apprenant souhaite atteindre
    target_points = models.PositiveIntegerField(default=0, verbose_name="Objectif de points")

    # Catégories qui intéressent l'apprenant (relation ManyToMany)
    interests = models.ManyToManyField(Category, blank=True, verbose_name="Intérêts")




    # Niveau de compétence de l'apprenant (choix prédéfinis)
    level = models.CharField(
        max_length=50, 
        choices=[
            ('Débutant', 'Débutant'), 
            ('Intermédiaire', 'Intermédiaire'), 
            ('Avancé', 'Avancé')
        ], 
        verbose_name="Niveau",
        default='Débutant'
    )
    
    
    class Meta:
        verbose_name = "Apprenant"
        verbose_name_plural = "Apprenants"

    def __str__(self):
        return self.user.username

    def get_completed_tasks(self):
        return self.user.task_set.filter(is_completed=True)

    def get_incomplete_tasks(self):
        """
        Récupère la liste des tâches non terminées par l'apprenant.
        """
        return self.user.task_set.filter(is_completed=False)

    def get_total_study_time(self):
        """
        Calcule le temps total passé en étude par l'apprenant.
        """
        activities = Activity.objects.filter(user=self.user, activity_type='étude')
        total_time = sum([activity.duration for activity in activities if activity.duration], timedelta())
        return total_time





class Report(models.Model):
    """
    Modèle pour les rapports de bug, suggestions ou retours.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Utilisateur")
    report_type = models.CharField(
        max_length=20,
        choices=(
            ('bug', 'Bug'),
            ('suggestion', 'Suggestion'),
            ('feedback', 'Retour'),
        ),
        verbose_name="Type de rapport"
    )
    description = models.TextField(verbose_name="Description")
    submitted_on = models.DateTimeField(auto_now_add=True, verbose_name="Date de soumission")

    class Meta:
        verbose_name = "Rapport"
        verbose_name_plural = "Rapports"

    def __str__(self):
        return f"{self.report_type.capitalize()} de {self.user.username} - {self.submitted_on}"






class Message(models.Model):
    """
    Modèle pour les messages envoyés dans les discussions.
    """
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages', verbose_name="Expéditeur")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages', verbose_name="Destinataire")
    content = models.TextField(verbose_name="Contenu du message")
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name="Envoyé le")

    class Meta:
        verbose_name = "Message"
        verbose_name_plural = "Messages"

    def __str__(self):
        return f"Message de {self.sender.username} à {self.receiver.username} le {self.sent_at}"





class Room(models.Model):
    """
    Modèle pour les salles de discussion.
    """
    name = models.CharField(max_length=100, verbose_name="Nom de la salle")
    slug = models.SlugField(unique=True, verbose_name="Slug")

    class Meta:
        verbose_name = "Salle"
        verbose_name_plural = "Salles"

    def __str__(self):
        return self.name





class ChatMessage(models.Model):
    """
    Modèle pour les messages dans une salle de chat.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Utilisateur")
    content = models.TextField(verbose_name="Contenu du message")
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='messages', verbose_name="Salle de chat")
    created_on = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")

    class Meta:
        verbose_name = "Message de chat"
        verbose_name_plural = "Messages de chat"

    def __str__(self):
        return f"Message de {self.user.username} dans {self.room.name} à {self.created_on}"






class Product(models.Model):
    name = models.CharField(max_length=255, verbose_name="Nom du produit")
    description = models.TextField(verbose_name="Description du produit")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Prix")

    def __str__(self):
        return self.name









class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Utilisateur")
    created_on = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")

    class Meta:
        verbose_name = "Panier"
        verbose_name_plural = "Paniers"

    def __str__(self):
        return f"Panier de {self.user.username}"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items', verbose_name="Panier")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Produit")
    quantity = models.PositiveIntegerField(verbose_name="Quantité")

    class Meta:
        verbose_name = "Article de panier"
        verbose_name_plural = "Articles de panier"

    def __str__(self):
        return f"{self.quantity} x {self.product.name} dans le panier de {self.cart.user.username}"





class PaymentService(models.Model):
   
    """
    Modèle pour les paiements des services.
    """

    # Type de service pour lequel le paiement est effectué (ex: cours, abonnement, etc.)
    service_type = models.CharField(max_length=50, verbose_name="Type de service")

    # Apprenant qui effectue le paiement
    learner = models.ForeignKey(Learner, on_delete=models.CASCADE, related_name='payments', verbose_name="Apprenant")

    # Session associée au paiement (optionnel, peut être NULL si le paiement n'est pas lié à une session spécifique)
    session = models.ForeignKey(Session, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Session associée")

    # Montant du paiement
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Prix")

    # Moyen de paiement utilisé (choix prédéfinis : carte ou mobile)
    payment_means = models.CharField(
        max_length=50,
        choices=(
            ('carte', 'Carte'),
            ('mobile', 'Mobile')
        ),
        verbose_name="Moyen de paiement"
    )

    # Statut du paiement (choix prédéfinis : en attente, payé, remboursé)
    status = models.CharField(
        max_length=20,
        choices=(
            ('en attente', 'En attente'),
            ('payé', 'Payé'),
            ('remboursé', 'Remboursé')
        ),
        default='en attente',
        verbose_name="Statut du paiement"
    )

    # Date et heure de création du paiement (enregistrée automatiquement)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")

    class Meta:
        verbose_name = "Service de paiement"
        verbose_name_plural = "Services de paiement"
        ordering = ['-created_at']
        db_table = 'payment_service'


    def __str__(self):
        return f"Paiement {self.id} - {self.learner.user.username} - {self.service_type}"

    def clean(self):
        """
        Validation personnalisée pour s'assurer que le prix est positif.
        """
        if self.price <= 0:
            raise ValidationError("Le prix doit être positif.")
    def __str__(self):
        return self.name

    




class File(models.Model):
    """
    Modèle pour stocker les fichiers téléchargés par les utilisateurs.
    """

    # Nom du fichier (pour l'affichage)
    name = models.CharField(max_length=200, verbose_name="Nom du fichier")

    # Fichier téléchargé (stocké sur le système de fichiers)
    file = models.FileField(upload_to='uploads/', verbose_name="Fichier")

    # Utilisateur qui a téléchargé le fichier
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Téléchargé par")

    # Date et heure de téléchargement (enregistrée automatiquement à la création)
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de téléchargement")

    # Cours associé au fichier (optionnel, peut être NULL si le fichier n'est pas lié à un cours)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Cours associé")

    class Meta:
        verbose_name = "Fichier"
        verbose_name_plural = "Fichiers"

    def __str__(self):
        return self.name





        

class Enrollment(models.Model):
    """
    Modèle pour suivre les inscriptions des apprenants aux cours.
    """

    # Apprenant inscrit au cours
    learner = models.ForeignKey(Learner, on_delete=models.CASCADE, related_name='enrollments', verbose_name="Apprenant")

    # Cours auquel l'apprenant est inscrit
    course = models.ForeignKey(Course, on_delete=models.CASCADE, verbose_name="Cours")

    # Date et heure d'inscription (enregistrée automatiquement à la création)
    enrolled_at = models.DateTimeField(auto_now_add=True, verbose_name="Date d'inscription")

    # Date et heure d'achèvement du cours (optionnel, peut être NULL si le cours n'est pas encore terminé)
    date_completed = models.DateTimeField(null=True, blank=True, verbose_name="Date d'achèvement")

    class Meta:
        verbose_name = "Inscription"
        verbose_name_plural = "Inscriptions"

        # Assurer l'unicité d'une inscription par apprenant pour un cours donné
        unique_together = ['learner', 'course']

    def __str__(self):
        return f"{self.learner} inscrit à {self.course}"




class MentorProfile(models.Model):
    """
    Modèle pour stocker des informations supplémentaires sur les mentors.
    """

    # Relation OneToOne avec le modèle Mentor, assurant qu'un mentor a un seul profil
    mentor = models.OneToOneField(Mentor, on_delete=models.CASCADE, verbose_name="Mentor")

    # Biographie du mentor
    bio = models.TextField(blank=True, verbose_name="Biographie")

    # Qualifications et diplômes du mentor
    qualifications = models.TextField(blank=True, verbose_name="Qualifications")

    # Autres champs potentiellement utiles :

    # Années d'expérience en tant que mentor ou dans le domaine d'expertise
    experience_years = models.PositiveIntegerField(null=True, blank=True, verbose_name="Années d'expérience")

    # URL de la page LinkedIn du mentor
    linkedin_url = models.URLField(blank=True, null=True, verbose_name="Profil LinkedIn")

    # URL du portfolio ou du site web personnel du mentor
    website_url = models.URLField(blank=True, null=True, verbose_name="Site web personnel")

    # Autres réseaux sociaux ou plateformes pertinentes
    # Par exemple : github_url, twitter_url, etc.

    class Meta:
        verbose_name = "Profil de mentor"
        verbose_name_plural = "Profils de mentors"

    def __str__(self):
        return f"Profil de {self.mentor.user.username}"
    
    


class Assignment(models.Model):
    """
    Modèle pour les devoirs assignés aux apprenants.
    """

    # Titre du devoir
    title = models.CharField(max_length=200, verbose_name="Titre du devoir")

    # Description détaillée du devoir
    description = models.TextField(verbose_name="Description")

    # Date et heure d'échéance du devoir
    due_date = models.DateTimeField(verbose_name="Date d'échéance")

    # Cours auquel le devoir est associé
    course = models.ForeignKey(Course, on_delete=models.CASCADE, verbose_name="Cours associé")

    # Apprenant à qui le devoir est assigné
    learner = models.ForeignKey(Learner, on_delete=models.CASCADE, related_name='assignments', verbose_name="Apprenant")

    # Statut du devoir (en cours, soumis, noté, etc.)
    status = models.CharField(
        max_length=20,
        choices=(
            ('en cours', 'En cours'),
            ('soumis', 'Soumis'),
            ('noté', 'Noté'),
            # ... autres statuts possibles
        ),
        default='en cours',
        verbose_name="Statut"
    )

    # Date et heure de création du devoir (enregistrée automatiquement)
    created_at = models.DateTimeField(default=datetime(2024, 1, 1, 0, 0, 0))

    # Date et heure de la dernière modification du devoir (mise à jour automatiquement)
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Date de modification")

    class Meta:
        verbose_name = "Devoir"
        verbose_name_plural = "Devoirs"

    def __str__(self):
        return self.title

    def clean(self):
        """
        Validation personnalisée pour s'assurer que la date d'échéance est dans le futur.
        """
        if self.due_date <= timezone.now():
            raise ValidationError("La date d'échéance doit être dans le futur.")




class PointProgress(models.Model):
    learner = models.OneToOneField(Learner, on_delete=models.CASCADE, related_name='progression_points')  # Modification ici
    current_points = models.PositiveIntegerField(default=0, verbose_name="Points actuels")
    target_points = models.PositiveIntegerField(default=0, verbose_name="Objectif de points")
    
    class Meta:
        verbose_name = "Progression des points"
        verbose_name_plural = "Progressions des points"

    def __str__(self):
        return f"Progression de {self.learner} : {self.current_points} / {self.target_points}"




# ==============================Mes différentes models pour le RAG ======================================



class Conversation(models.Model):
    """
    Modèle pour stocker l'historique des conversations avec le RAG.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Utilisateur")
    start_time = models.DateTimeField(auto_now_add=True, verbose_name="Début de la conversation")

    class Meta:
        verbose_name = "Conversation"
        verbose_name_plural = "Conversations"

    def __str__(self):
        return f"Conversation de {self.user.username} commencée le {self.start_time}"


class ConversationMessage(models.Model):
    """
    Modèle pour stocker les messages individuels d'une conversation avec le RAG.
    """
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=20, choices=[('user', 'Utilisateur'), ('rag', 'RAG')], verbose_name="Expéditeur")
    content = models.TextField(verbose_name="Contenu du message")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Horodatage")

    class Meta:
        verbose_name = "Message de conversation"
        verbose_name_plural = "Messages de conversation"

    def __str__(self):
        return f"Message de {self.sender} dans la conversation {self.conversation.id}"


class ReferenceDocument(models.Model):
    """
    Modèle pour stocker les documents de référence utilisés par le RAG.
    """
    title = models.CharField(max_length=255, verbose_name="Titre du document")
    file = models.FileField(upload_to='reference_documents/', verbose_name="Fichier")

    class Meta:
        verbose_name = "Document de référence"
        verbose_name_plural = "Documents de référence"

    def __str__(self):
        return self.title