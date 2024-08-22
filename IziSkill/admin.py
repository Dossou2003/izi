from django.contrib import admin
from .models import Room,Message
from .models import Cart, CartItem
# bourjon/admin.py

from .models import PaymentService, Resource, Assignment,MentorProfile, Enrollment, File

# Register your models here.

from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Session, Mentor, Learner, PaymentService, Category, SubCategory, Course, Resource, Rating, Task, Activity

# Inline pour les évaluations
class RatingInline(admin.TabularInline):  # Ou StackedInline pour un affichage vertical
    model = Rating
    extra = 1  # Nombre de champs vides supplémentaires à afficher


# Personnalisation de l'affichage de l'utilisateur
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'status', 'is_staff','is_active','points')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('username', 'email')
    fieldsets = (
        (None, {'fields': ('username', 'password', 'email')}),
        ('Informations personnelles', {'fields': ('first_name', 'last_name', 'image', 'status')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Dates importantes', {'fields': ('last_login', 'date_joined')}),
    )


class SessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'learner', 'mentor', 'start_time', 'duration', 'status_session', 'pricing')
    list_filter = ('status_session', 'mentor', 'learner')
    search_fields = ('learner__user__username', 'mentor__user__username')


class MentorAdmin(admin.ModelAdmin):
    list_display = ('user', 'specialty', 'rate', 'average_rating')
    list_filter = ('specialty',)
    search_fields = ('user__username', 'specialty')
    inlines = [RatingInline]




class LearnerAdmin(admin.ModelAdmin):
    list_display = ('user', 'level', 'target_points')
    list_filter = ('level', )
    search_fields = ('user__username',)

    def get_interests(self, obj):
        return ", ".join([category.name for category in obj.interests.all()])
    get_interests.short_description = 'Intérêts'




class PaymentServiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'learner', 'service_type', 'price', 'payment_means', 'status', 'created_at')
    list_filter = ('service_type', 'payment_means', 'status')
    search_fields = ('learner__user__username', 'service_type')
    readonly_fields = ('created_at',)  # Empêcher la modification de la date de création







class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    list_filter = ('category',)
    search_fields = ('name', 'category__name')


class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'sub_category', 'episode_number', 'difficulty_level')
    list_filter = ('sub_category__category', 'difficulty_level')
    search_fields = ('title', 'sub_category__name', 'sub_category__category__name')


class ResourceAdmin(admin.ModelAdmin):
    list_display = ('name',  
 'resource_type', 'file', 'link')
    list_filter = ('resource_type',)
    search_fields = ('name',)
    
        

class ActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'activity_type', 'start_time', 'end_time', 'duration')
    list_filter = ('activity_type',)
    search_fields = ('user__username',)

    def duration(self, obj):
        return obj.duration
    duration.short_description = 'Durée'  # Nom de la colonne dans l'interface d'administration


class TaskAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'course', 'due_time', 'is_completed')
    list_filter = ('is_completed', 'course__sub_category__category')  # Filtrer par catégorie du cours
    search_fields = ('name', 'course__title')




class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 1

class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_on')
    inlines = [CartItemInline]



class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'learner', 'due_date', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'course__sub_category__category')  # Filtrer par catégorie du cours
    search_fields = ('title', 'course__title', 'learner__user__username')
    readonly_fields = ('created_at', 'updated_at')  # Empêcher la modification des dates


class MentorProfileAdmin(admin.ModelAdmin):
    list_display = ('mentor', 'experience_years')  # Champs à afficher dans la liste
    search_fields = ('mentor__user__username', 'qualifications')


class EnrollmentAdmin(admin.ModelAdmin):  

    list_display = ('learner', 'course', 'enrolled_at', 'date_completed')
    list_filter = ('course', 'date_completed')
    search_fields = ('learner__user__username', 'course__title')
    readonly_fields = ('enrolled_at', )  # Empêcher la modification de la date d'inscription



class FileAdmin(admin.ModelAdmin):
    list_display = ('name',  
 'uploaded_by', 'course', 'uploaded_at')
    list_filter = ('uploaded_by', 'course')
    search_fields = ('name', 'uploaded_by__username', 'course__title')
    readonly_fields = ('uploaded_at',)  # Empêcher la modification de la date de téléchargement


# Enregistrement des modèles dans l'interface d'administration
# Enregistrement des modèles dans l'interface d'administration
admin.site.register(User, UserAdmin)
admin.site.register(Session, SessionAdmin)
admin.site.register(Mentor, MentorAdmin)
admin.site.register(Learner, LearnerAdmin)
admin.site.register(PaymentService, PaymentServiceAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(SubCategory, SubCategoryAdmin)
admin.site.register(Course, CourseAdmin)
admin.site.register(Resource, ResourceAdmin)
admin.site.register(Task, TaskAdmin)
admin.site.register(Activity, ActivityAdmin)
admin.site.register(Room)
admin.site.register(Message)
admin.site.register(Cart, CartAdmin)
admin.site.register(CartItem)
admin.site.register(Rating)
admin.site.register(Assignment,AssignmentAdmin) 
admin.site.register(MentorProfile,MentorProfileAdmin)
admin.site.register(Enrollment,EnrollmentAdmin)
admin.site.register(File, FileAdmin)
