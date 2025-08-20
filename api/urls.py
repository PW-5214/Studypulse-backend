from django.urls import path
from . import views # Import views from the current directory

# Define the application namespace
app_name = 'api'

# Define URL patterns for the API app
urlpatterns = [
    path('hello/', views.hello_world, name='hello_world'),
    
    # Course URLs
    path('courses/', views.CourseListView.as_view(), name='course-list'),
    path('courses/<int:pk>/', views.CourseDetailView.as_view(), name='course-detail'),

    # Progress Tracker URL
    path('progress-tracker/', views.progress_tracker_data, name='progress-tracker'),

    # Mark Lesson Complete URL
    path('lessons/<int:lesson_id>/complete/', views.mark_lesson_complete, name='lesson-complete'),

    # Summarization Tool URL
    path('tools/summarize/', views.summarize_media, name='summarize-media'),

    # Case Study Tool URL
    path('tools/generate-case-study/', views.generate_case_study, name='generate-case-study'),

    # Quiz URLs
    path('quizzes/<int:pk>/', views.QuizDetailView.as_view(), name='quiz-detail'),
    path('quizzes/submit/', views.submit_quiz, name='quiz-submit'),

    # Chatbot URL
    path('chatbot/message/', views.chatbot_interaction, name='chatbot-message'),

    # Assignment Checker URL (New)
    path('assignment-checker/', views.assignment_checker, name='assignment-checker'),

    # Profile Management URL (New)
    path('profile/', views.UserProfileView.as_view(), name='user-profile'),

    # TODO: Add URLs for other features:
    # - Personalized recommendations
    # - Progress tracking (e.g., /progress/, /progress/<lesson_id>/complete/)
    # - Quizzes (e.g., /quizzes/, /quizzes/<quiz_id>/take/)
    # - Tools (e.g., /tools/video-summary/)
    # - Chatbot
    # - Profile

    # Add paths for your API endpoints here
    # e.g., path('user/dashboard/', views.user_dashboard, name='user_dashboard'),
    # path('chatbot/', views.chatbot_interaction, name='chatbot'),
] 