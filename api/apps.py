from django.apps import AppConfig
import firebase_admin
from firebase_admin import credentials
import os, json
from django.conf import settings


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        print("\n--- Attempting Firebase Admin SDK Initialization (in apps.py) ---")  # START LOG
        if not firebase_admin._apps:
            try:
                # Check for ENV variable (Railway)
                firebase_key = os.environ.get("FIREBASE_KEY")

                if firebase_key:
                    print("Firebase key found in environment. Loading from ENV...")
                    cred = credentials.Certificate(json.loads(firebase_key))
                else:
                    # Fallback to local file (for development)
                    key_path = os.path.join(settings.BASE_DIR, "firebase-service-account-key.json")
                    print(f"Looking for Firebase service account key at: {key_path}")
                    if not os.path.exists(key_path):
                        raise FileNotFoundError("Firebase key not found in ENV or local file.")
                    cred = credentials.Certificate(key_path)

                firebase_admin.initialize_app(cred)
                print("\n*******************************************************")
                print("  ✅ Firebase Admin SDK initialized successfully.")
                print("*******************************************************\n")

            except Exception as e:
                print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                print(f"  ❌ ERROR initializing Firebase Admin SDK: {e}")
                print("  Firebase authentication WILL FAIL.")
                print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
        else:
            print("Firebase Admin SDK already initialized.")
        print("--- Firebase Admin SDK Initialization Check Complete ---\n")
