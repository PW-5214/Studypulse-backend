from django.apps import AppConfig
import firebase_admin
from firebase_admin import credentials
import os
from django.conf import settings

class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        print("\n--- Attempting Firebase Admin SDK Initialization (in apps.py) ---") # START LOG
        # Initialize Firebase Admin SDK only once
        if not firebase_admin._apps:
            key_path = os.path.join(settings.BASE_DIR, 'firebase-service-account-key.json')
            print(f"Looking for Firebase service account key at: {key_path}") # Log path
            if os.path.exists(key_path):
                print("Service account key file FOUND.") # Log found
                try:
                    print("Attempting to load credentials...")
                    cred = credentials.Certificate(key_path)
                    print("Credentials loaded successfully.")
                    print("Attempting to initialize Firebase app...")
                    firebase_admin.initialize_app(cred)
                    # SUCCESS LOG
                    print("\n*******************************************************")
                    print("  Firebase Admin SDK initialized successfully.")
                    print("*******************************************************\n")
                except Exception as e:
                    # FAILURE LOG (Load/Init Error)
                    print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                    print(f"  ERROR initializing Firebase Admin SDK: {e}")
                    print("  Firebase authentication WILL FAIL.")
                    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n") 
            else:
                # FAILURE LOG (File Not Found)
                print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                print(f"  ERROR: Firebase service account key NOT FOUND at the expected path.")
                print("  Firebase authentication WILL FAIL.")
                print("  Please ensure 'firebase-service-account-key.json' is in the 'backend' directory.")
                print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
        else:
            print("Firebase Admin SDK already initialized.") # Log already done
        print("--- Firebase Admin SDK Initialization Check Complete ---\n") # END LOG

# Make sure this AppConfig is registered in settings.INSTALLED_APPS (it should be 'api') 