from django.shortcuts import render
from django.http import JsonResponse
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes, parser_classes, authentication_classes
from rest_framework.response import Response
from django.contrib.auth.models import User
import time
import google.generativeai as genai
from django.conf import settings
from rest_framework.parsers import MultiPartParser, FormParser
from datetime import datetime
from rest_framework.permissions import AllowAny # Import AllowAny
from .firebase_auth import FirebaseAuthentication # Import the custom auth class
import os
from django.utils import timezone
from django.db import transaction
from .models import Quiz, Question, Choice, QuizAttempt, Answer, UserProfile # Ensure all needed models are imported
from .serializers import QuizAttemptSerializer # Import serializer for result
import json # To potentially parse history if sent as JSON string

# Import models and serializers
from .models import UserProfile, LearningTopic, Course, Module, Lesson, UserProgress, Badge, UserBadge, Quiz
from .serializers import (
    UserProfileSerializer, LearningTopicSerializer, CourseSerializer, 
    ModuleSerializer, LessonSerializer, UserProgressSerializer, 
    BadgeSerializer, UserBadgeSerializer, QuizSerializer, QuizAttemptSerializer
)

# Create your views here.

# Example view using DRF decorator:
@api_view(['GET'])
@permission_classes([AllowAny]) # Explicitly allow anyone to access this simple view
def hello_world(request):
    """A simple API endpoint to test the connection."""
    return Response({'message': 'Hello from StudyPulse Backend (via DRF)!'})

# --- Learning Content Views ---

class CourseListView(generics.ListAPIView):
    """ API endpoint to list all available courses. """
    queryset = Course.objects.select_related('topic').prefetch_related('modules__lessons').all()
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly] # Allow anyone to view, auth to modify (if CreateAPIView is added)

class CourseDetailView(generics.RetrieveAPIView):
    """ API endpoint to retrieve details of a single course. """
    queryset = Course.objects.select_related('topic').prefetch_related('modules__lessons').all()
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    # lookup_field = 'pk' # or 'slug' if you add a slug field to Course

# --- Personalized Learning / Progress Views ---

@api_view(['POST'])
# @permission_classes([permissions.IsAuthenticated]) # Keep previous state (AllowAny)
@permission_classes([permissions.IsAdminUser]) # Only staff/admin users can mark complete
def mark_lesson_complete(request, lesson_id):
    """ Marks a lesson as complete FOR A USER (specified in request) BY AN ADMIN and awards XP. """
    # Since only admins can call this, they need to specify WHICH user to update.
    # Let's expect 'user_id' in the request data.
    target_user_id = request.data.get('user_id') 
    if not target_user_id:
        return Response({'error': 'user_id missing in request body (specify which user to update)'}, status=status.HTTP_400_BAD_REQUEST)
        
    try:
        target_user = User.objects.get(pk=target_user_id)
        user_profile = target_user.profile # Get the profile of the target user
    except User.DoesNotExist:
        return Response({'error': 'Target user not found for provided user_id.'}, status=status.HTTP_404_NOT_FOUND)
    except User.profile.RelatedObjectDoesNotExist:
         return Response({'error': 'Target user does not have a profile.'}, status=status.HTTP_404_NOT_FOUND)

    # Get the lesson
    try:
        lesson = Lesson.objects.get(pk=lesson_id)
    except Lesson.DoesNotExist:
        return Response({'error': 'Lesson not found.'}, status=status.HTTP_404_NOT_FOUND)

    # Check if already completed for the target user
    if UserProgress.objects.filter(user_profile=user_profile, lesson=lesson).exists():
        return Response({'message': f'Lesson already marked as complete for user {target_user.username}.'}, status=status.HTTP_200_OK)

    # Create progress record for the target user
    UserProgress.objects.create(user_profile=user_profile, lesson=lesson)

    # Award XP to the target user
    xp_awarded = lesson.xp_value
    user_profile.xp += xp_awarded
    user_profile.save()

    # TODO: Implement level up logic if needed (check if new XP crosses a threshold)
    # TODO: Implement logic to check if any Badges are earned based on completion for the target user

    return Response({
        'message': f'Lesson "{lesson.title}" marked as complete for user {target_user.username}. Admin: {request.user.username}',
        'xp_awarded': xp_awarded,
        'new_total_xp': user_profile.xp
    }, status=status.HTTP_201_CREATED)

@api_view(['GET'])
# @permission_classes([permissions.IsAuthenticated]) # Keep previous state (AllowAny)
@permission_classes([permissions.AllowAny]) # Allow any GET request
def progress_tracker_data(request):
    """
    API endpoint to fetch data needed for the Progress Tracker page:
    - Leaderboard (top users by XP)
    - Current user's badges (will be empty)
    - Placeholder performance data
    """
    # 1. Leaderboard Data (Top 10 users by XP)
    top_users_profiles = UserProfile.objects.select_related('user').order_by('-xp')[:10]
    leaderboard_serializer = UserProfileSerializer(top_users_profiles, many=True)

    # 2. Current User's Badges - Return empty list as no user context
    user_badges_serializer = UserBadgeSerializer([], many=True) # Empty data

    # 3. Topics vs Performance Data (Placeholder)
    topic_performance = [
        {'topic': 'Data Science', 'performance': 85},
        {'topic': 'DBMS', 'performance': 70},
        {'topic': 'DSA', 'performance': 90},
    ]

    # 4. Weekly/Monthly Graphs Data (Placeholder)
    weekly_progress_data = {
        'labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        'data': [20, 30, 15, 40, 25, 50, 35]
    }
    monthly_progress_data = {
        'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
        'data': [100, 150, 200, 180, 250, 300]
    }

    return Response({
        'leaderboard': leaderboard_serializer.data,
        'my_badges': user_badges_serializer.data, # Return empty list
        'topic_performance': topic_performance,
        'weekly_graph': weekly_progress_data,
        'monthly_graph': monthly_progress_data
    })

# --- Video/Audio Summarization View ---

@api_view(['POST'])
@authentication_classes([FirebaseAuthentication]) 
@permission_classes([permissions.IsAuthenticated]) 
@parser_classes([MultiPartParser, FormParser]) 
def summarize_media(request):
    """
    API endpoint to upload a video/audio file and get a transcript + summary.
    Expects a file named 'file' in the multipart/form-data.
    Optionally accepts 'prompt' and 'model_name' fields.
    """
    # 1. --- Configure API Key (HARDCODED - NOT RECOMMENDED FOR PRODUCTION) ---
    # WARNING: Hardcoding API keys is insecure. Prefer environment variables.
    api_key = "AIzaSyCI6eePyXO3c6DLUZUq8ZumbBEGiOnQgeM" # NEW User-provided key
    if not api_key:
        return Response({"error": "Server configuration error: Hardcoded Google API key is missing."}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    try:
        genai.configure(api_key=api_key)
        print("GenAI configured using NEW hardcoded API key.") 
    except Exception as e:
        print(f"Error configuring GenAI with hardcoded key: {e}")
        return Response({"error": "Server configuration error: Could not configure Google AI."}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # 2. --- Get File from Request ---
    file_obj = request.FILES.get('file')
    if not file_obj:
        return Response({"error": "No file provided. Please upload a file named 'file'."}, 
                        status=status.HTTP_400_BAD_REQUEST)

    # 3. --- Get Optional Parameters ---
    user_prompt = request.data.get('prompt', '')
    # Use a specific model from the list provided earlier, default to flash
    # TODO: Validate the model name against allowed models if necessary
    model_name = request.data.get('model_name', 'gemini-1.5-flash') 
    
    # Define models available (consider moving this to settings or a constants file)
    AVAILABLE_MODELS = [
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        # Add other models as needed and available
    ]
    if model_name not in AVAILABLE_MODELS:
         return Response({"error": f"Invalid model name '{model_name}'. Available: {AVAILABLE_MODELS}"},
                         status=status.HTTP_400_BAD_REQUEST)

    try:
        # 4. --- Upload File to Google AI ---
        print(f"Uploading file '{file_obj.name}' ({type(file_obj)}) to Google AI...")
        
        file_path_or_bytes = None
        try:
            # Try getting temp path first (better for large files)
            file_path_or_bytes = file_obj.temporary_file_path()
            print(f"Using temporary file path: {file_path_or_bytes}")
        except AttributeError:
            # If no temporary path (likely InMemoryUploadedFile), read the bytes
            print(f"File '{file_obj.name}' is in memory, reading bytes...")
            file_obj.seek(0) # Ensure reading from the start
            file_path_or_bytes = file_obj.read()
            print(f"Read {len(file_path_or_bytes) if isinstance(file_path_or_bytes, bytes) else 'N/A'} bytes from in-memory file.")
        
        if file_path_or_bytes is None:
             return Response({"error": "Could not access file content for upload."}, 
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Use the extracted path or bytes for upload
        print(f"Calling genai.upload_file with path/bytes: {type(file_path_or_bytes)}") # DEBUG
        uploaded_file = genai.upload_file(path=file_path_or_bytes, display_name=file_obj.name)
        # ADDED LOGGING HERE:
        print(f"genai.upload_file call completed.") # DEBUG
        print(f"File Uploaded: Name='{uploaded_file.name}', DisplayName='{uploaded_file.display_name}', State='{uploaded_file.state.name}'") # DEBUG

        # 5. --- Wait for Processing ---
        while uploaded_file.state.name == "PROCESSING":
            print(f"Waiting for '{uploaded_file.name}' processing...")
            time.sleep(10) # Poll every 10 seconds
            # Need to refetch the file object to get updated state
            uploaded_file = genai.get_file(uploaded_file.name)
            print(f"File State: {uploaded_file.state.name}")

        if uploaded_file.state.name == "FAILED":
            print(f"File Processing Failed: {uploaded_file.name}")
            return Response({"error": "File processing failed on the Google AI server."}, 
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        if uploaded_file.state.name != "ACTIVE":
             print(f"File is not active after processing: {uploaded_file.name}, State: {uploaded_file.state.name}")
             return Response({"error": f"File processing ended in unexpected state: {uploaded_file.state.name}"},
                             status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 6. --- Generate Content ---
        print(f"Generating content using {model_name}...")
        model = genai.GenerativeModel(model_name=model_name)
        
        # Construct the prompt (using default if user prompt is empty)
        if not user_prompt or user_prompt.isspace():
            # Using the detailed default prompt structure from the script
            current_date = datetime.now().strftime("%B %d, %Y")
            prompt = f"""Please analyze the provided media and provide a detailed response in the following format:

## Transcript:
Provide a detailed transcript with timestamps in [HH:MM:SS] format where applicable.

## Summary:
Media Title: {file_obj.name}
Date: {current_date}

Key Points (with timestamps if possible):
- Point 1 [HH:MM:SS]
- Point 2 [HH:MM:SS]

Discussion Topics:
- Topic 1 ([HH:MM:SS - HH:MM:SS])
  - Detail

Action Items:
- Item 1 (Assigned: ?, Timestamp: [HH:MM:SS])

Conclusions:
[Summary of final decisions and next steps with timestamps]

Note: Please ensure summaries are supported by timestamps where possible."""
        else:
            prompt = user_prompt
        
        # Make the API call (increase timeout for potentially long generation)
        response = model.generate_content([uploaded_file, prompt], request_options={"timeout": 600})
        
        # 7. --- Parse and Return Response ---
        # Use a simplified parsing approach for now
        try:
            # Basic split - assumes response strictly follows the ## headers
            parts = response.text.split('## Summary:', 1)
            transcript_part = parts[0].replace('## Transcript:', '').strip()
            summary_part = parts[1].strip() if len(parts) > 1 else "Summary could not be parsed."
        except Exception as parse_error:
             print(f"Error parsing response text: {parse_error}")
             # Return the raw text if parsing fails
             transcript_part = response.text
             summary_part = "Could not parse summary from response."

        return Response({
            'transcript': transcript_part,
            'summary': summary_part,
            'model_used': model_name
        }, status=status.HTTP_200_OK)

    except Exception as e:
        # Log the full error trace
        print(f"Error during media summarization: {e}") 
        # Consider more specific error handling based on potential Google API errors
        return Response({"error": f"An unexpected error occurred: {str(e)}"}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    finally:
        # Optional: Clean up the uploaded file on Google AI side? 
        # Only do this if you are sure you won't need it again.
        # try:
        #     if 'uploaded_file' in locals() and uploaded_file:
        #         genai.delete_file(uploaded_file.name)
        #         print(f"Deleted uploaded file: {uploaded_file.name}")
        # except Exception as delete_error:
        #     print(f"Error deleting uploaded file '{uploaded_file.name}': {delete_error}")
        pass # Avoid deletion for now

# --- Case Study Generation View ---

@api_view(['POST'])
@authentication_classes([FirebaseAuthentication]) # Use Firebase auth
@permission_classes([permissions.IsAuthenticated]) # Require user to be logged in
def generate_case_study(request):
    """
    API endpoint to generate a case study based on a user-provided topic/prompt.
    Expects 'prompt' in the request body.
    """
    # 1. --- Configure API Key (Using the same hardcoded key as summarize_media for now) ---
    # WARNING: Hardcoding API keys is insecure.
    # WARNING: Ensure this key is VALID and the API is enabled.
    api_key = "AIzaSyCDzQWz5ptcwVRr568GO2an681zTTaOtSk" # Should match the one in summarize_media
    if not api_key:
        return Response({"error": "Server configuration error: Google API key not set."}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    try:
        genai.configure(api_key=api_key)
        print("GenAI configured for Case Study Generation.") 
    except Exception as e:
        print(f"Error configuring GenAI: {e}")
        return Response({"error": "Server configuration error: Could not configure Google AI."}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # 2. --- Get Prompt from Request ---
    user_prompt = request.data.get('prompt')
    if not user_prompt or not user_prompt.strip():
        return Response({"error": "Please provide a topic or prompt for the case study."}, 
                        status=status.HTTP_400_BAD_REQUEST)

    # 3. --- Prepare Prompt for AI ---
    # Enhance the user prompt to guide the AI
    generation_prompt = f"""Generate a detailed and insightful case study based on the following topic or request:

**Topic/Request:** {user_prompt}

**Instructions for Case Study:**
- Clearly define the problem or situation.
- Provide relevant background information.
- Describe the challenges faced.
- Detail the actions taken or solutions implemented.
- Analyze the results and outcomes.
- Conclude with key takeaways or lessons learned.
- Ensure the case study is well-structured, informative, and engaging.

**Generated Case Study:**
"""
    
    # 4. --- Call Generative Model ---
    try:
        print(f"Generating case study for prompt starting with: {user_prompt[:50]}...")
        # Choose an appropriate model (consider gemini-pro for better text generation)
        model = genai.GenerativeModel(model_name='gemini-1.5-flash') # Or 'gemini-1.5-pro'
        response = model.generate_content(generation_prompt, request_options={"timeout": 180}) # Adjust timeout if needed
        
        generated_text = response.text
        print("Case study generation successful.")

        return Response({
            'case_study_text': generated_text
        }, status=status.HTTP_200_OK)

    except Exception as e:
        # Log the full error trace for debugging
        import traceback
        print(f"Error during case study generation: {e}")
        print(traceback.format_exc())
        # Consider more specific error handling for Google API errors if needed
        return Response({"error": f"Failed to generate case study: {str(e)}"}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# --- Quiz Views ---

class QuizDetailView(generics.RetrieveAPIView):
    """ API endpoint to retrieve details of a single quiz (questions & choices). """
    queryset = Quiz.objects.prefetch_related('questions__choices').all()
    serializer_class = QuizSerializer
    # Apply Firebase authentication
    authentication_classes = [FirebaseAuthentication]
    permission_classes = [permissions.IsAuthenticated] 
    # lookup_field = 'pk' # pk is the default

# --- Submit Quiz View ---
@api_view(['POST'])
@authentication_classes([FirebaseAuthentication])
@permission_classes([permissions.IsAuthenticated])
def submit_quiz(request):
    """
    API endpoint to submit answers for a quiz, calculate results, and award XP.
    Expects: 
        - quiz_id: ID of the Quiz being submitted.
        - answers: Dictionary mapping question_id (str) to selected_choice_id (int).
                   e.g., { "15": 23, "16": 28 }
    """
    quiz_id = request.data.get('quiz_id')
    user_answers_dict = request.data.get('answers') # { "question_id": choice_id, ... }

    if not quiz_id or user_answers_dict is None:
        return Response({"error": "Missing quiz_id or answers."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        quiz = Quiz.objects.prefetch_related('questions__choices').get(pk=quiz_id)
    except Quiz.DoesNotExist:
        return Response({"error": "Quiz not found."}, status=status.HTTP_404_NOT_FOUND)

    user_profile = request.user.profile
    total_questions = quiz.questions.count()
    correct_answers_count = 0
    attempt = None

    if total_questions == 0:
        return Response({"error": "Quiz has no questions."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        with transaction.atomic(): # Ensure all saves succeed or fail together
            # 1. Create QuizAttempt record
            attempt = QuizAttempt.objects.create(
                user_profile=user_profile,
                quiz=quiz,
                is_complete=False # Mark complete after processing answers
            )
            print(f"Created QuizAttempt {attempt.id} for user {user_profile.id} on quiz {quiz_id}")

            # 2. Process and save each Answer
            for question_id_str, selected_choice_id in user_answers_dict.items():
                try:
                    question_id = int(question_id_str)
                    question = quiz.questions.get(pk=question_id) # More efficient way to get related question
                    selected_choice = Choice.objects.get(pk=selected_choice_id, question=question) # Ensure choice belongs to question
                    
                    is_correct = selected_choice.is_correct
                    if is_correct:
                        correct_answers_count += 1
                    
                    Answer.objects.create(
                        quiz_attempt=attempt,
                        question=question,
                        selected_choice=selected_choice,
                        is_correct=is_correct
                    )
                    print(f"Saved answer for Q:{question_id} -> C:{selected_choice_id} (Correct: {is_correct})")
                
                except Question.DoesNotExist:
                    print(f"Warning: Question ID {question_id_str} not found in Quiz {quiz_id}. Skipping answer.")
                    continue # Skip this answer if question doesn't belong to quiz
                except Choice.DoesNotExist:
                     print(f"Warning: Choice ID {selected_choice_id} not found or doesn't belong to Question {question_id_str}. Skipping answer.")
                     continue # Skip this answer if choice is invalid
                except ValueError:
                     print(f"Warning: Invalid Question ID format: {question_id_str}. Skipping answer.")
                     continue # Skip if question_id isn't an int

            # 3. Calculate Score and update attempt
            score = round((correct_answers_count / total_questions) * 100, 2) if total_questions > 0 else 0
            passed = score >= quiz.pass_threshold
            
            attempt.score = score
            attempt.passed = passed
            attempt.is_complete = True
            attempt.end_time = timezone.now()
            attempt.save()
            print(f"QuizAttempt {attempt.id} finalized. Score: {score}%, Passed: {passed}")

            # 4. Award XP if passed
            if passed:
                user_profile.xp += quiz.xp_reward
                user_profile.save()
                print(f"Awarded {quiz.xp_reward} XP to user {user_profile.id}. New XP: {user_profile.xp}")
            
            # 5. Serialize and return the results
            result_serializer = QuizAttemptSerializer(attempt)
            return Response(result_serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        # Log the error
        import traceback
        print(f"Error during quiz submission processing: {e}")
        print(traceback.format_exc())
        # Clean up potentially created attempt if transaction fails mid-way
        # (transaction.atomic should handle rollback, but good practice to be aware)
        if attempt and not attempt.is_complete:
             print(f"Attempting cleanup of incomplete QuizAttempt {attempt.id}")
             # attempt.delete() # Or decide on cleanup strategy
             pass 
        return Response({"error": f"An error occurred while submitting the quiz: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# TODO: Add views for:
# - Listing Quizzes (perhaps filtered by module/course)
# - Starting a QuizAttempt (POST request) - (Covered by submit_quiz for now)
# - Getting QuizAttempt results (Could be the response from submit_quiz or a separate GET view)

# --- Other Placeholder Views (To be implemented) ---

# @api_view(['GET'])
# @permission_classes([permissions.IsAuthenticated]) # Example permission
# def user_dashboard(request):
#     user_profile = request.user.profile
#     serializer = UserProfileSerializer(user_profile)
#     # TODO: Add logic to fetch dashboard stats, recommendations etc.
#     dashboard_data = serializer.data
#     dashboard_data['stats'] = [...] # Fetch stats
#     dashboard_data['recommendations'] = [...] # Fetch recommendations
#     return Response(dashboard_data)

# --- Chatbot Interaction View ---

@api_view(['POST'])
@authentication_classes([FirebaseAuthentication]) # Use Firebase auth
@permission_classes([permissions.IsAuthenticated]) # Require user to be logged in
def chatbot_interaction(request):
    """
    API endpoint for interacting with the chatbot.
    Expects 'message' and optionally 'history' in the request body.
    'history' should be a list of dictionaries: [{'role': 'user'/'model', 'parts': ['text']}]
    """
    # 1. --- Configure API Key (Using the same hardcoded key) ---
    # WARNING: Hardcoding is insecure. Ensure this key is VALID.
    api_key = "AIzaSyCDzQWz5ptcwVRr568GO2an681zTTaOtSk" 
    if not api_key:
        return Response({"error": "Server configuration error: Google API key not set."}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    try:
        genai.configure(api_key=api_key)
        # print("GenAI configured for Chatbot.") # Reduce logging noise
    except Exception as e:
        print(f"Error configuring GenAI: {e}")
        return Response({"error": "Server configuration error: Could not configure Google AI."}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # 2. --- Get Message and History from Request ---
    user_message = request.data.get('message')
    history_data = request.data.get('history', []) # Default to empty list

    if not user_message or not user_message.strip():
        return Response({"error": "Please provide a message."}, 
                        status=status.HTTP_400_BAD_REQUEST)

    # Basic validation/parsing if history is sent as a JSON string (optional)
    # try:
    #     if isinstance(history_data, str):
    #         history = json.loads(history_data)
    #     else:
    #         history = history_data # Assume it's already a list/dict structure
    #     if not isinstance(history, list):
    #          raise ValueError("History must be a list.")
    # except (json.JSONDecodeError, ValueError) as e:
    #      return Response({"error": f"Invalid history format: {e}"}, status=status.HTTP_400_BAD_REQUEST)
    
    # Use history_data directly assuming frontend sends correct format
    history = history_data

    # 3. --- Call Generative Model (Chat) ---
    try:
        print(f"Generating chatbot response for: {user_message[:50]}...")
        model = genai.GenerativeModel(model_name='gemini-1.5-flash') 
        
        # Start chat with existing history
        chat = model.start_chat(history=history)
        
        # Send the new user message
        response = chat.send_message(user_message)
        
        ai_response_text = response.text.strip()
        print("Chatbot response generation successful.")

        return Response({
            'reply': ai_response_text
            # Optionally return the updated history from chat.history if needed
        }, status=status.HTTP_200_OK)

    except Exception as e:
        import traceback
        print(f"Error during chatbot interaction: {e}")
        print(traceback.format_exc())
        return Response({"error": f"Failed to get chatbot response: {str(e)}"}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Add views for:
# - Personalized Learning (Roadmap, Recommendations)
# - Progress Tracking (Leaderboard, Performance Table)
# - Voice & Video Tools (Upload, Summary, Transcription)
# - Case Study/AR Models
# - Gamified Quizzes
# - Assignment Checker
# - Profile Management
# - Authentication (Login/Signup)

# --- AI Assignment Checker View ---
@api_view(['POST'])
@authentication_classes([FirebaseAuthentication]) # Add Firebase Authentication
@permission_classes([permissions.IsAuthenticated]) # Keep permission check
def assignment_checker(request):
    """
    API endpoint to receive assignment text and return AI-generated feedback
    on correctness and clarity.
    """
    # --- Configure API Key and Model *inside* the view (like other views) ---
    # WARNING: Hardcoding API keys is insecure. Use settings or environment variables.
    api_key = "AIzaSyCDzQWz5ptcwVRr568GO2an681zTTaOtSk" # User-provided key
    checker_model = None
    try:
        genai.configure(api_key=api_key)
        checker_model = genai.GenerativeModel('gemini-1.5-flash')
        print("AssignmentChecker: GenAI configured using hardcoded key.")
    except Exception as e:
        print(f"AssignmentChecker: Error configuring GenAI with hardcoded key: {e}")
        return Response({'error': 'AI model configuration failed inside view.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    # --- End of local configuration ---

    # The original check is now less likely to fail, but keep it as safeguard
    if not checker_model:
        return Response({'error': 'AI model could not be initialized.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    assignment_text = request.data.get('assignment_text', '')
    # Optional: Add subject/context later if needed
    # subject_context = request.data.get('context', 'General assignment')

    if not assignment_text.strip():
        return Response({'error': 'Assignment text cannot be empty.'}, status=status.HTTP_400_BAD_REQUEST)

    # Basic length check to prevent overly long requests (adjust as needed)
    if len(assignment_text) > 15000: # Increased limit slightly
         return Response({'error': 'Assignment text is too long (max 15,000 characters).'}, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

    # Modified prompt: Removed the request for Originality Assessment
    prompt = f"""
    Analyze the following assignment text submitted by a student. Provide feedback on the following aspects:

    1.  **Correctness:** Briefly evaluate the potential factual accuracy and correctness of the content based on general knowledge. Point out any obvious errors or questionable statements. Be concise.
    2.  **Clarity & Structure:** Assess the clarity of the writing, the logical flow of ideas, and the overall structure. Suggest specific improvements if needed. Be concise.

    Present the feedback clearly, using markdown formatting with sections for **Correctness** and **Clarity & Structure**.

    Assignment Text:
    ---BEGIN ASSIGNMENT---
    {assignment_text}
    ---END ASSIGNMENT---
    """

    try:
        # Use safety settings appropriate for student work analysis
        safety_settings = {
            'HATE': 'BLOCK_MEDIUM_AND_ABOVE',
            'HARASSMENT': 'BLOCK_MEDIUM_AND_ABOVE',
            'SEXUAL' : 'BLOCK_MEDIUM_AND_ABOVE',
            'DANGEROUS' : 'BLOCK_MEDIUM_AND_ABOVE'
        }
        response = checker_model.generate_content(prompt, safety_settings=safety_settings)

        # Check for blocked content *before* accessing response.text
        if response.prompt_feedback.block_reason:
            block_reason = response.prompt_feedback.block_reason
            print(f"Gemini Block Reason: {block_reason}")
            return Response({'error': f'Content blocked by AI safety filters ({block_reason}). Please revise the text.'}, status=status.HTTP_400_BAD_REQUEST)

        # Get feedback and append the disclaimer
        feedback_text = response.text
        disclaimer = "\n\n---\n**Note:** This feedback focuses on correctness and clarity. For plagiarism detection against external sources, please use a dedicated plagiarism checking tool."
        full_feedback = feedback_text + disclaimer

        return Response({'feedback': full_feedback}, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"Error calling Gemini for assignment check: {e}")
        # Simplified error handling slightly as block reason is checked earlier
        return Response({'error': 'Failed to get feedback from AI. An internal error occurred.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# --- Profile Management View ---

class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    API endpoint for retrieving and updating the logged-in user's profile.
    Handles GET (retrieve) and PUT/PATCH (update).
    """
    serializer_class = UserProfileSerializer
    authentication_classes = [FirebaseAuthentication] # Use Firebase auth
    permission_classes = [permissions.IsAuthenticated] # Must be logged in

    def get_object(self):
        """ Override to return the UserProfile linked to the request.user """
        # UserProfile is created via a signal when User is created,
        # so it should always exist for an authenticated user.
        # If not, something went wrong during signup.
        try:
            return self.request.user.profile
        except UserProfile.DoesNotExist:
            # This case should ideally not happen for authenticated users
            # Maybe log an error or handle appropriately
            raise exceptions.NotFound("UserProfile not found for the logged-in user.")