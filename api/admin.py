from django.contrib import admin
from .models import (
    UserProfile, LearningTopic, Course, Module, Lesson, 
    UserProgress, Badge, UserBadge,
    # Import new Quiz models
    Quiz, Question, Choice, QuizAttempt, Answer 
)

# Register your models here.

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'level', 'xp')

@admin.register(LearningTopic)
class LearningTopicAdmin(admin.ModelAdmin):
    list_display = ('title',)

class LessonInline(admin.TabularInline): 
    model = Lesson
    extra = 1
    ordering = ('order',)
    
    # Use fieldsets to group and potentially hide/show fields based on content_type
    # This is a basic example; more complex logic might require custom forms or JavaScript
    fieldsets = (
        (None, {
            'fields': ('order', 'title', 'content_type', 'xp_value')
        }),
        ('Text Content', {
            'classes': ('collapse', 'content-type-text'), # Use CSS classes for potential JS toggle
            'fields': ('text_content',)
        }),
        ('YouTube Video', {
            'classes': ('collapse', 'content-type-youtube'),
            'fields': ('youtube_video_id',)
        }),
        ('External Link', {
            'classes': ('collapse', 'content-type-external_link'),
            'fields': ('external_url',)
        }),
    )
    
    # Note: Simple hiding/showing fields purely based on choices in Django admin without 
    # saving first is tricky. The 'collapse' class provides a hook for potential 
    # custom JavaScript to handle dynamic display if needed.
    # For now, all fields will be visible but grouped.

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order')
    list_filter = ('course',)
    inlines = [LessonInline]
    ordering = ('course', 'order')

class ModuleInline(admin.TabularInline):
    model = Module
    extra = 1
    ordering = ('order',)
    show_change_link = True # Allows editing module directly from course

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'topic')
    list_filter = ('topic',)
    inlines = [ModuleInline]

@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ('user_profile', 'lesson', 'completed_at')
    list_filter = ('user_profile__user', 'lesson__module__course') # Filter by user or course
    readonly_fields = ('completed_at',)

@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'icon_emoji')

@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ('user_profile', 'badge', 'earned_at')
    list_filter = ('user_profile__user', 'badge')
    readonly_fields = ('earned_at',)

# --- Quiz Admin Registrations ---

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 3 # Show 3 blank choices by default

class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'quiz', 'order')
    list_filter = ('quiz',)
    inlines = [ChoiceInline]

class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    show_change_link = True
    # Exclude Choice inline within Question inline to avoid nesting issues

class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'module', 'pass_threshold', 'xp_reward')
    list_filter = ('module__course__topic', 'module__course')
    inlines = [QuestionInline]

class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0 # Don't show blank answers by default
    readonly_fields = ('question', 'selected_choice', 'is_correct') # Make fields read-only

class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('user_profile', 'quiz', 'score', 'passed', 'is_complete', 'start_time', 'end_time')
    list_filter = ('quiz', 'passed', 'is_complete', 'user_profile')
    readonly_fields = ('start_time', 'end_time') # Make timestamps read-only
    inlines = [AnswerInline]

admin.site.register(Quiz, QuizAdmin)
admin.site.register(Question, QuestionAdmin)
# Choice is managed via QuestionAdmin inline
admin.site.register(QuizAttempt, QuizAttemptAdmin)
# Answer is managed via QuizAttemptAdmin inline 