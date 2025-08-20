from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class UserProfile(models.Model):
    """Extends the default Django User model to store additional profile information."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    level = models.PositiveIntegerField(default=1)
    xp = models.PositiveIntegerField(default=0, help_text="Experience Points")
    bio = models.TextField(blank=True, null=True)
    # Add other profile fields here if needed:
    # avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

# Signal to automatically create/update UserProfile when User is created/saved
# This is often placed in models.py or a separate signals.py file
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    instance.profile.save()


class LearningTopic(models.Model):
    """Represents a subject or topic that users can learn about."""
    title = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    # Potential future fields:
    # parent_topic = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='subtopics')
    # difficulty_level = models.CharField(max_length=50, choices=[('Beginner', 'Beginner'), ('Intermediate', 'Intermediate'), ('Advanced', 'Advanced')], default='Beginner')

    def __str__(self):
        return self.title

# --- Content Structure Models ---

class Course(models.Model):
    """ Represents a full course composed of modules. """
    topic = models.ForeignKey(LearningTopic, on_delete=models.PROTECT, related_name='courses')
    title = models.CharField(max_length=255)
    description = models.TextField()
    # created_at = models.DateTimeField(auto_now_add=True)
    # updated_at = models.DateTimeField(auto_now=True)
    # prerequisites = models.ManyToManyField('self', blank=True, symmetrical=False)
    # estimated_duration = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.title

class Module(models.Model):
    """ Represents a module within a course. """
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0, help_text="Order within the course")

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.course.title} - {self.title}"

class Lesson(models.Model):
    """ Represents a single lesson within a module. """
    CONTENT_TYPES = (
        ('text', 'Text Content'),
        ('youtube', 'YouTube Video'),
        ('external_link', 'External Link'),
        # Add other types as needed
        # ('quiz', 'Quiz Link'), 
        # ('ar_model', 'AR/3D Model Link'),
    )
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=255)
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES, default='text')
    
    # Specific content fields (make them nullable/blankable)
    text_content = models.TextField(blank=True, null=True, help_text="Content for text lessons.")
    youtube_video_id = models.CharField(max_length=50, blank=True, null=True, help_text="Only the YouTube video ID (e.g., dQw4w9WgXcQ)")
    external_url = models.URLField(blank=True, null=True, help_text="URL for external resources.")
    # quiz = models.ForeignKey('Quiz', on_delete=models.SET_NULL, null=True, blank=True) # Example for quiz link
    # ar_model = models.ForeignKey('ARModel', on_delete=models.SET_NULL, null=True, blank=True) # Example for AR link
    
    # Remove the old generic 'content' field (will require migration handling)
    # content = models.TextField(help_text="Text content, video URL, quiz ID, external URL, AR model ID, etc.")
    
    order = models.PositiveIntegerField(default=0, help_text="Order within the module")
    xp_value = models.PositiveIntegerField(default=10, help_text="XP awarded for completing this lesson") # Uncommented XP

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.module.title} - {self.title}"

# --- User Progress Tracking ---

class UserProgress(models.Model):
    """ Tracks a user's completion status for lessons. """
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='progress')
    completed_at = models.DateTimeField(auto_now_add=True)
    # Add more fields if needed, e.g., score for quizzes linked via lesson

    class Meta:
        unique_together = ('user_profile', 'lesson') # User can complete a lesson only once
        ordering = ['-completed_at']

    def __str__(self):
        return f"{self.user_profile.user.username} completed {self.lesson.title}"

# --- Badge Models ---

class Badge(models.Model):
    """ Represents an achievable badge. """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    icon_emoji = models.CharField(max_length=10, blank=True, help_text="Emoji character for the badge (e.g., 🏆)")
    # icon_image = models.ImageField(upload_to='badge_icons/', null=True, blank=True) # Alternative image upload
    # criteria = models.JSONField(null=True, blank=True) # Could store criteria for automatic awarding

    def __str__(self):
        return self.name

class UserBadge(models.Model):
    """ Links a UserProfile to a Badge they have earned. """
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name='earned_by')
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user_profile', 'badge') # User earns a badge only once
        ordering = ['-earned_at']

    def __str__(self):
        return f"{self.user_profile.user.username} earned {self.badge.name}"


# --- Placeholder Models (To be defined later) ---
# class Quiz(models.Model): ...
# class Question(models.Model): ...
# class Answer(models.Model): ...
# class UserSubmission(models.Model): ...
# class ChatHistory(models.Model): ...
# class Certificate(models.Model): ...
# class ARModel(models.Model): ...
# class CaseStudy(models.Model): ...


# Add models for:
# - Course / Module / Lesson structure (linking to LearningTopic)
# - UserProgress (linking UserProfile and specific content like Lesson or Quiz)
# - Quizzes, Questions, Answers
# - User Submissions (Assignments, Videos)
# - Chat History
# - Certificates
# - AR Models
# - Case Studies
# - etc.


# Example UserProfile model (extend Django's User)
# class UserProfile(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE)
#     # Add fields like profile picture, level, badges, etc.
#     level = models.IntegerField(default=1)
#     # ...

#     def __str__(self):
#         return self.user.username

# Add models for:
# - Learning Topics
# - User Progress
# - Quizzes, Questions, Answers
# - User Submissions (Assignments, Videos)
# - Chat History
# - Certificates
# - AR Models
# - Case Studies
# - etc. 

# --- Gamified Quiz Models --- 

class Quiz(models.Model):
    module = models.ForeignKey(Module, related_name='quizzes', on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    pass_threshold = models.PositiveIntegerField(default=70, help_text="Percentage required to pass (e.g., 70)")
    xp_reward = models.PositiveIntegerField(default=50, help_text="XP awarded for passing the quiz")

    def __str__(self):
        return f"{self.title} (Module: {self.module.title})"

class Question(models.Model):
    quiz = models.ForeignKey(Quiz, related_name='questions', on_delete=models.CASCADE)
    text = models.TextField()
    # Add question_type later if needed (e.g., MULTIPLE_CHOICE, TRUE_FALSE)
    # question_type = models.CharField(max_length=20, default='MULTIPLE_CHOICE')
    order = models.PositiveIntegerField(default=0, help_text="Order of the question within the quiz")

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Q{self.order}: {self.text[:50]}... (Quiz: {self.quiz.title})"

class Choice(models.Model):
    question = models.ForeignKey(Question, related_name='choices', on_delete=models.CASCADE)
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"Choice: {self.text[:50]}... (Question: {self.question.id})"

class QuizAttempt(models.Model):
    user_profile = models.ForeignKey(UserProfile, related_name='quiz_attempts', on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, related_name='attempts', on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True, help_text="Score as a percentage")
    passed = models.BooleanField(default=False)
    is_complete = models.BooleanField(default=False)

    def __str__(self):
        return f"Attempt by {self.user_profile.user.username} on {self.quiz.title} (Score: {self.score}%)"

class Answer(models.Model):
    quiz_attempt = models.ForeignKey(QuizAttempt, related_name='answers', on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(Choice, on_delete=models.CASCADE, null=True, blank=True)
    # Add fields for other answer types later if needed (e.g., text_answer for fill-in-the-blank)
    # text_answer = models.TextField(blank=True, null=True)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"Answer to Q{self.question.order} in Attempt {self.quiz_attempt.id}" 