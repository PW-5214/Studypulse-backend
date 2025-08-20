from rest_framework import serializers
from .models import UserProfile, LearningTopic, Course, Module, Lesson, UserProgress, Badge, UserBadge, Choice, Question, Quiz, Answer, QuizAttempt # Import specific models
from django.contrib.auth.models import User

# Create your serializers here.

# --- User Serializers ---

class UserSerializer(serializers.ModelSerializer):
    """ Basic User Serializer - Used for nesting AND updating """
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id', 'username', 'email'] # Prevent username/email changes via profile update

class UserProfileSerializer(serializers.ModelSerializer):
    """ User Profile Serializer for retrieving and updating """
    # Nest UserSerializer, but make it writable for specific fields
    user = UserSerializer() # Removed read_only=True

    class Meta:
        model = UserProfile
        # Add 'bio' to fields, remove level/xp from direct update
        fields = ['id', 'user', 'bio', 'level', 'xp']
        read_only_fields = ['id', 'level', 'xp'] # Level/XP shouldn't be updated directly

    def update(self, instance, validated_data):
        # Handle nested User update
        user_data = validated_data.pop('user', None)
        user = instance.user
        if user_data:
            # Update only allowed fields from the nested serializer
            user.first_name = user_data.get('first_name', user.first_name)
            user.last_name = user_data.get('last_name', user.last_name)
            # Add other allowed user fields if needed
            user.save()

        # Update UserProfile fields (e.g., bio)
        instance.bio = validated_data.get('bio', instance.bio)
        # Add other profile fields if needed
        instance.save()
        return instance

# --- Content Serializers ---

class LearningTopicSerializer(serializers.ModelSerializer):
    """ Serializer for Learning Topics """
    class Meta:
        model = LearningTopic
        fields = ['id', 'title', 'description']

class LessonSerializer(serializers.ModelSerializer):
    """ Serializer for Lessons, including specific content fields """
    class Meta:
        model = Lesson
        # Include all relevant fields for displaying lesson content
        fields = [
            'id', 'title', 'content_type', 'order', 'xp_value', 
            'text_content', 'youtube_video_id', 'external_url'
            # Add quiz, ar_model fields when those models/serializers exist
            ]
        # Depending on use case, you might make some fields read_only

class ModuleSerializer(serializers.ModelSerializer):
    """ Serializer for Modules, including nested Lessons """
    lessons = LessonSerializer(many=True, read_only=True)
    # Add progress calculation fields if needed
    class Meta:
        model = Module
        fields = ['id', 'title', 'description', 'order', 'lessons']

class CourseSerializer(serializers.ModelSerializer):
    """ Serializer for Courses, including nested Modules """
    modules = ModuleSerializer(many=True, read_only=True)
    topic = LearningTopicSerializer(read_only=True) # Show topic details
    # Add overall progress calculation fields if needed
    class Meta:
        model = Course
        fields = ['id', 'title', 'description', 'topic', 'modules']

# --- Progress Serializer ---

class UserProgressSerializer(serializers.ModelSerializer):
    """ Serializer for User Progress (primarily for tracking completion) """
    # Optionally nest lesson/user details if needed, but keep simple for now
    # lesson = LessonSerializer(read_only=True)
    # user_profile = UserProfileSerializer(read_only=True) 
    lesson_id = serializers.PrimaryKeyRelatedField(queryset=Lesson.objects.all(), source='lesson')

    class Meta:
        model = UserProgress
        fields = ['id', 'user_profile', 'lesson_id', 'completed_at']
        read_only_fields = ['user_profile', 'completed_at'] # User profile set from request

# --- Badge Serializers ---

class BadgeSerializer(serializers.ModelSerializer):
    """ Serializer for Badges """
    class Meta:
        model = Badge
        fields = ['id', 'name', 'description', 'icon_emoji'] # Add icon_image if used

class UserBadgeSerializer(serializers.ModelSerializer):
    """ Serializer for UserBadges, showing Badge details """
    badge = BadgeSerializer(read_only=True)
    class Meta:
        model = UserBadge
        fields = ['id', 'badge', 'earned_at']

# --- Quiz Serializers ---

class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        # Exclude 'is_correct' when sending data for taking a quiz
        fields = ['id', 'text'] 

class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'text', 'order', 'choices']

class QuizSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = ['id', 'title', 'description', 'module', 'questions']

# Serializers for results (can include is_correct)
class CorrectChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'text', 'is_correct']

class AnswerSerializer(serializers.ModelSerializer):
    # Optionally nest selected_choice details if needed
    # selected_choice = CorrectChoiceSerializer(read_only=True)
    class Meta:
        model = Answer
        fields = ['id', 'question', 'selected_choice', 'is_correct']

class QuizAttemptSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True, read_only=True)
    # Optionally nest quiz details
    # quiz = QuizSerializer(read_only=True) 
    class Meta:
        model = QuizAttempt
        fields = ['id', 'quiz', 'user_profile', 'start_time', 'end_time', 'score', 'passed', 'is_complete', 'answers']

# Example User Serializer
# class UserSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = User
#         fields = ['id', 'username', 'email', 'first_name', 'last_name'] # Add other fields as needed

# Example UserProfile Serializer
# class UserProfileSerializer(serializers.ModelSerializer):
#     user = UserSerializer(read_only=True) # Nest the user serializer
#     class Meta:
#         model = UserProfile
#         fields = '__all__' # Or specify fields explicitly

# Add serializers for all your models that need API representation:
# - LearningTopicSerializer
# - ProgressSerializer
# - QuizSerializer
# - SubmissionSerializer
# - ChatMessageSerializer
# - etc. 