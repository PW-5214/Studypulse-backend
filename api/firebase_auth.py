import firebase_admin
from firebase_admin import auth, credentials
from rest_framework import authentication, exceptions
from django.contrib.auth.models import User
import os
from django.conf import settings

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
            decoded_token = auth.verify_id_token(id_token)
            print("Firebase Auth: Token verification successful.")
            
            firebase_uid = decoded_token.get('uid')
            email = decoded_token.get('email')
            print(f"Firebase Auth: Token decoded - UID: {firebase_uid}, Email: {email}")
            
            if not firebase_uid or not email:
                print("Firebase Auth: ERROR - Invalid token claims (missing UID or email)")
                raise exceptions.AuthenticationFailed('Invalid token claims (missing UID or email)')

            print(f"Firebase Auth: Getting or creating Django user for email: {email}")
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email, 
                }
            )
            print(f"Firebase Auth: User {'created' if created else 'found'}: {user.username}")
            return (user, decoded_token)

        except auth.ExpiredIdTokenError as e:
            print(f"Firebase Auth: ERROR - Token expired: {e}")
            raise exceptions.AuthenticationFailed('Firebase ID token has expired.')
        except auth.RevokedIdTokenError as e:
            print(f"Firebase Auth: ERROR - Token revoked: {e}")
            raise exceptions.AuthenticationFailed('Firebase ID token has been revoked.')
        except auth.InvalidIdTokenError as e:
            print(f"Firebase Auth: ERROR - Invalid ID Token: {e}")
            raise exceptions.AuthenticationFailed(f'Invalid Firebase ID token: {e}')
        except User.DoesNotExist:
            print(f"Firebase Auth: ERROR - User.DoesNotExist (unexpected with get_or_create)")
            raise exceptions.AuthenticationFailed('Could not find or create Django user.')
        except Exception as e:
            import traceback
            print(f"Firebase Auth: UNEXPECTED ERROR during authentication: {e}")
            print(traceback.format_exc())
            raise exceptions.AuthenticationFailed(f'Firebase authentication failed: {e}')

    def authenticate_header(self, request):
        return 'Bearer realm="Firebase"' 