import firebase_admin
from firebase_admin import auth, credentials
from rest_framework import authentication, exceptions
from django.contrib.auth.models import User
import os
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class FirebaseAuthentication(authentication.BaseAuthentication):
    """
    Custom Django Rest Framework authentication backend for Firebase ID tokens.
    Verifies the Bearer token provided in the Authorization header using the
    Firebase Admin SDK and links it to a Django User.
    """
    def authenticate(self, request):
        print("Attempting Firebase Authentication...")
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            print("Firebase Auth: No Authorization header found.")
            return None 

        parts = auth_header.split()
        if len(parts) == 0:
            print("Firebase Auth: Authorization header is empty.")
            return None
        
        if parts[0].lower() != 'bearer' or len(parts) != 2:
            print(f"Firebase Auth: Invalid Authorization header format: {parts[0]}")
            return None 

        id_token = parts[1]
        print(f"Firebase Auth: Received Bearer token, attempting verification...")

        try:
            if not firebase_admin._apps:
                print("Firebase Auth: ERROR - SDK not initialized. Trying fallback init (NOT RECOMMENDED)...")
                key_path = os.path.join(settings.BASE_DIR, 'firebase-service-account-key.json')
                if os.path.exists(key_path):
                     try:
                         cred = credentials.Certificate(key_path)
                         firebase_admin.initialize_app(cred)
                         print("Firebase Auth: Fallback SDK initialization successful.")
                     except Exception as init_e:
                         print(f"Firebase Auth: FATAL - Fallback SDK initialization FAILED: {init_e}")
                         raise exceptions.AuthenticationFailed('Firebase Admin SDK could not be initialized.')
                else:
                     print(f"Firebase Auth: FATAL - Service key not found at {key_path} for fallback init.")
                     raise exceptions.AuthenticationFailed('Firebase Admin SDK service key not found.')
            
            print("Firebase Auth: Calling auth.verify_id_token()...")
            # Get decoded token info
            decoded_token = auth.verify_id_token(id_token)
            uid = decoded_token.get('uid')
            email = decoded_token.get('email')

            logger.info(f"Firebase Auth: Token decoded - UID: {uid}, Email: {email}")

            # Modified user lookup logic
            try:
                # Try to get existing user
                user = User.objects.filter(email=email).first()
                if not user:
                    # Create new user if none exists
                    user = User.objects.create_user(
                        username=email,
                        email=email
                    )
                    logger.info(f"Firebase Auth: Created new user for email: {email}")
                else:
                    logger.info(f"Firebase Auth: Found existing user for email: {email}")
                
                return (user, None)

            except Exception as e:
                logger.error(f"Firebase Auth: Error processing user: {str(e)}")
                raise exceptions.AuthenticationFailed('User authentication failed')

        except Exception as e:
            logger.error(f"Firebase Auth: Authentication failed: {str(e)}")
            raise exceptions.AuthenticationFailed('Invalid token')

    def authenticate_header(self, request):
        return 'Bearer realm="Firebase"'