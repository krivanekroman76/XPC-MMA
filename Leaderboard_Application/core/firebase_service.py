import os
import requests
import json
import urllib.parse # Make sure this is imported at the top of your file
#from config_manager import ConfigManager

class FirebaseService:
    def __init__(self, language="en"):
        self.logger = None
        self.id_token = None
        self.local_id = None
        self.uid = None
        self.user_info = {}
        self.language = language
        
        # Load translation dictionary
        self.i18n = self._load_translations()
        
        try:
            config = ConfigManager.load_json('firebase-config.json')
            if not config:
                print(self._t("err_config_missing"))
                return
                
            self.api_key = config["apiKey"]
            self.project_id = config["projectId"]
            self.db_url = f"https://firestore.googleapis.com/v1/projects/{self.project_id}/databases/(default)/documents"
            
            self.log(self._t("init_success", project_id=self.project_id))
            
        except FileNotFoundError:
            print(self._t("err_config_missing"))
        except Exception as e:
            print(self._t("err_config_load", error=str(e)))

    # --- LOCALIZATION & LOGGING ---
    
    def _load_translations(self):
        """Loads strings from the respective language JSON file."""
        return ConfigManager.load_json(f'lang/{self.language}.json', {})

    def _t(self, key, **kwargs):
        """Fetches the translation and formats it with provided kwargs."""
        text = self.i18n.get(key, f"[{key}]")
        try:
            return text.format(**kwargs)
        except KeyError:
            return text

    def log(self, message):
        """Logs messages using a custom logger or standard print."""
        if self.logger:
            self.logger(f"[Firebase] {message}")
        else:
            print(f"[Firebase] {message}")

    # --- REST API HELPERS ---
    
    def _format_for_firestore(self, data):
        """Converts standard Python dictionaries to Firestore REST API format."""
        if isinstance(data, str): return {"stringValue": data}
        if isinstance(data, bool): return {"booleanValue": data}
        if isinstance(data, int): return {"integerValue": str(data)}
        if isinstance(data, float): return {"doubleValue": data}
        if isinstance(data, list): 
            return {"arrayValue": {"values": [self._format_for_firestore(v) for v in data]}}
        if isinstance(data, dict): 
            return {"mapValue": {"fields": {k: self._format_for_firestore(v) for k, v in data.items()}}}
        if data is None: return {"nullValue": None}
        return {"stringValue": str(data)}

    def _parse_firestore_document(self, doc_data):
        """Parses Firestore REST API format back to standard Python dictionaries."""
        parsed = {}
        if 'fields' in doc_data:
            for key, val in doc_data['fields'].items():
                if 'stringValue' in val: parsed[key] = val['stringValue']
                elif 'booleanValue' in val: parsed[key] = val['booleanValue']
                elif 'integerValue' in val: parsed[key] = int(val['integerValue'])
                elif 'doubleValue' in val: parsed[key] = val['doubleValue']
                elif 'arrayValue' in val: 
                    values = val['arrayValue'].get('values', [])
                    parsed[key] = [self._parse_firestore_document({'fields': {'temp': v}})['temp'] for v in values]
                elif 'mapValue' in val: parsed[key] = self._parse_firestore_document(val['mapValue'])
        return parsed

    def _parse_firestore_value(self, value):
        """Helper to parse a single Firestore value."""
        if 'stringValue' in value: return value['stringValue']
        if 'integerValue' in value: return int(value['integerValue'])
        return str(value)

    def _get_headers(self):
        """Returns authorization headers for requests."""
        if not self.id_token: return {}
        return {"Authorization": f"Bearer {self.id_token}"}

    def _refresh_id_token(self):
        """
        Automatically refreshes the Auth token when it expires (tokens expire every 1 hour).
        Returns True if successful, False otherwise.
        """
        if not hasattr(self, 'refresh_token') or not self.refresh_token:
            self.log("Refresh token missing. User must log in again.")
            return False
            
        url = f"https://securetoken.googleapis.com/v1/token?key={self.api_key}"
        
        # NOTE: The Google token endpoint expects form-urlencoded data, NOT a JSON payload.
        # Therefore, we must use 'data=payload' instead of 'json=payload' in the request.
        payload = {"grant_type": "refresh_token", "refresh_token": self.refresh_token}
        
        try:
            response = requests.post(url, data=payload)
            response.raise_for_status()
            data = response.json()
            
            # Update our local tokens with the newly generated ones
            self.id_token = data['id_token']
            self.refresh_token = data['refresh_token']
            
            self.log("ID Token successfully refreshed in the background.")
            return True
            
        except Exception as e:
            self.log(f"Token refresh failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                self.log(f"Refresh error details: {e.response.text}")
            return False

    def _make_request(self, method, url, **kwargs):
        """
        Smart wrapper for the Firestore REST API. 
        It automatically injects the auth token and handles silent token refreshes.
        """
        headers = self._get_headers()
        if 'headers' in kwargs:
            headers.update(kwargs['headers'])
        kwargs['headers'] = headers

        response = requests.request(method, url, **kwargs)
        
        # Check if the request failed due to an expired token.
        # Firebase sometimes returns 401 (Unauthorized), but it can also return 
        # 403 (Permission Denied) if Firestore security rules block the expired token.
        if response.status_code in [401, 403]:
            
            # Double-check that the 403 error is actually an auth issue, not a genuine rules violation
            if response.status_code == 401 or "missing or insufficient permissions" in response.text.lower():
                self.log(self._t("token_expired") + " Attempting auto-refresh...")
                
                if self._refresh_id_token():
                    # If the token was successfully refreshed, retry the exact same request
                    kwargs['headers'] = self._get_headers()
                    response = requests.request(method, url, **kwargs)
                else:
                    self.log("Auto-refresh failed. User is completely logged out and must restart the app.")
                    
        return response
    
    # --- AUTHENTICATION ---

    def login(self, email, password):
        """Logs in the user and fetches their custom data (role, league)."""
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={self.api_key}"
        payload = {"email": email, "password": password, "returnSecureToken": True}
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            self.id_token = data['idToken']
            self.refresh_token = data['refreshToken']
            self.uid = data['localId']
            self.local_id = self.uid 
            
            self.user_info = self.get_user_data(self.uid)
            return True, self._t("login_success")
        except Exception as e:
            return False, str(e)

    def get_user_data(self, uid):
        """Fetches user metadata from the Users collection."""
        if not self.id_token: return {"role": "user"}
        url = f"{self.db_url}/Users/{uid}"
        try:
            response = self._make_request("GET", url)
            if response.status_code == 200:
                return self._parse_firestore_document(response.json())
            return {"role": "user"}
        except Exception as e:
            self.log(f"Error fetching user data: {e}")
            return {"role": "user"}
    
    def get_all_users(self):
        """Fetches all users from the Users collection."""
        url = f"{self.db_url}/Users"
        try:
            response = self._make_request("GET", url)
            
            if response.status_code == 200:
                users = []
                for doc in response.json().get('documents', []):
                    # Extract the document ID (which is the user's UID) from the document path
                    user_id = doc.get('name', '').split('/')[-1]
                    parsed_data = self._parse_firestore_document(doc)
                    parsed_data['uid'] = user_id
                    users.append(parsed_data)
                return users
            else:
                self.log(f"Failed to fetch users. Status: {response.status_code}")
                return []
        except Exception as e:
            self.log(f"Error fetching all users: {e}")
            return []
                
    # --- USER MANAGEMENT (ADMIN TOOLS) ---
    
    def create_user_account(self, email, password, role, assigned_league="", allowed_races=None):
        """Creates an Auth account and writes user metadata to Firestore."""
        url_auth = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={self.api_key}"
        payload_auth = {"email": email, "password": password, "returnSecureToken": True}
        
        try:
            response = requests.post(url_auth, json=payload_auth)
            response.raise_for_status() 
            data = response.json()
            new_uid = data['localId'] 
            
            user_data = {"email": email, "role": role}
            if assigned_league: user_data["assigned_league"] = assigned_league
            if allowed_races: user_data["allowed_races"] = allowed_races
            
            firestore_payload = {"fields": {k: self._format_for_firestore(v) for k, v in user_data.items()}}
            url_db = f"{self.db_url}/Users/{new_uid}"
            
            db_response = self._make_request("PATCH", url_db, json=firestore_payload)
            db_response.raise_for_status()
            
            self.log(self._t("user_created", email=email, role=role))
            return True, "User successfully created!"
            
        except requests.exceptions.HTTPError as e:
            try:
                error_message = e.response.json().get('error', {}).get('message', 'Unknown error')
                if error_message == "EMAIL_EXISTS": return False, self._t("err_email_exists")
                elif "WEAK_PASSWORD" in error_message: return False, self._t("err_weak_password")
                return False, f"Firebase error: {error_message}"
            except:
                return False, f"Server error: {e}"
        except Exception as e:
            return False, str(e)

    def upload_single_translation(self, file_path):
        try:
            # 1. Extract language code from filename (e.g., 'cs.json' -> 'cs')
            lang_code = os.path.basename(file_path).replace('.json', '')
            self.log(f"[DEBUG] Attempting to upload translation for language: {lang_code}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # 2. Upload the translation dictionary
            firestore_payload = {
                "fields": {k: self._format_for_firestore(v) for k, v in data.items()}
            }
            url = f"{self.db_url}/Translations/{lang_code}"
            
            response = self._make_request("PATCH", url, json=firestore_payload)
            
            if response.status_code != 200:
                self.log(f"[CRITICAL] Upload failed. Details: {response.json()}")
                return False, f"Upload failed (Status {response.status_code})."
            
            self.log(f"[DEBUG] Main translation uploaded. Updating metadata...")

            # ==========================================
            # 3. NEW STEP: UPDATE THE METADATA VERSION
            # ==========================================
            meta_url = f"{self.db_url}/Translations/metadata"
            
            # Fetch current metadata to get the current version
            get_meta = self._make_request("GET", meta_url)
            current_version = 0
            
            if get_meta.status_code == 200:
                parsed_meta = self._parse_firestore_document(get_meta.json())
                # Get the current version, default to 0 if it doesn't exist yet
                current_version = parsed_meta.get(lang_code, 0)
                
            new_version = current_version + 1
            
            # Prepare the update payload for just this language
            meta_payload = {
                "fields": {
                    lang_code: self._format_for_firestore(new_version)
                }
            }
            
            # VERY IMPORTANT: Use updateMask so we don't overwrite other languages!
            patch_meta_url = f"{meta_url}?updateMask.fieldPaths={lang_code}"
            meta_resp = self._make_request("PATCH", patch_meta_url, json=meta_payload)
            
            if meta_resp.status_code == 200:
                success_msg = f"Successfully uploaded {lang_code.upper()}! (v{new_version})"
                self.log(f"[DEBUG] {success_msg}")
                return True, success_msg
            else:
                self.log(f"[CRITICAL] Metadata update failed. Details: {meta_resp.json()}")
                return False, "Translations uploaded, but metadata update failed!"

        except Exception as e:
            self.log(f"[CRITICAL] Exception during upload: {str(e)}")
            return False, f"Upload failed: {str(e)}"
        
    # --- LEAGUES AND RACES ---
    
    def create_league(self, name, abbreviation):
        """Creates a new league document."""
        doc_id = abbreviation.upper().replace(" ", "_")
        url = f"{self.db_url}/Leagues?documentId={doc_id}"
        
        payload = {
            "fields": {
                "name": {"stringValue": name},
                "abbreviation": {"stringValue": abbreviation}
            }
        }
        
        response = self._make_request("POST", url, json=payload)
        
        if response.status_code == 200:
            self.log(self._t("league_created", doc_id=doc_id))
            return doc_id
        elif response.status_code == 409:
            self.log(self._t("league_exists", doc_id=doc_id))
            return doc_id
        else:
            self.log(f"[CRITICAL] Error creating league. Status: {response.status_code}")
            return None

    def get_all_leagues(self):
        """Fetches all leagues."""
        url = f"{self.db_url}/Leagues"
        response = self._make_request("GET", url)
        
        if response.status_code != 200: return []
            
        leagues = []
        for doc in response.json().get('documents', []):
            doc_id = doc.get('name', '').split('/')[-1]
            fields = doc.get('fields', {})
            leagues.append({
                "id": doc_id,
                "name": fields.get('name', {}).get('stringValue', doc_id),
                "abbreviation": fields.get('abbreviation', {}).get('stringValue', doc_id)
            })
        return leagues

    def create_race(self, league_id, name, date_time, writer_uid):
        """Creates a race inside the nested Subcollection: /Leagues/{league_id}/Races"""
        if not league_id: return False

        # Create a URL-safe document ID by replacing spaces with underscores
        safe_doc_name = name.replace(" ", "_")
        # Ensure diacritics don't break the REST API URL
        safe_doc_id = urllib.parse.quote(safe_doc_name) 

        # Append ?documentId= to force Firestore to use our custom ID instead of generating one
        url = f"{self.db_url}/Leagues/{league_id}/Races?documentId={safe_doc_id}"
        
        # FIXED PAYLOAD: Using correct Firestore REST API types (mapValue, stringValue, integerValue)
        payload = {
            "fields": {
                "name": {"stringValue": name},
                "date_time": {"stringValue": date_time},
                "writer_uid": {"stringValue": writer_uid},
                "status": {"stringValue": "Preparing"},
                "settings": {
                    "mapValue": {
                        "fields": {
                            "preset": {"stringValue": "preset_pu_standard"},
                            "logic": {"stringValue": "attack"},
                            "lanes": {"integerValue": "1"}, # Note: REST API expects numbers as strings here
                            "attempts": {"integerValue": "1"},
                            "sections": {"integerValue": "1"},
                            "penalties": {"stringValue": "seconds"}
                        }
                    }
                }
            }
        }
        
        response = self._make_request("POST", url, json=payload)
        
        if response.status_code == 200:
            self.log(f"Race created successfully with ID: {safe_doc_name}")
            return True
        elif response.status_code == 409:
             # 409 means a document with this ID already exists!
             self.log(f"[Warning] Race with ID {safe_doc_name} already exists.")
             return False
        else:
            self.log(f"[CRITICAL] Failed to create race. Status: {response.status_code}")
            self.log(f"[CRITICAL] Firebase Response: {response.text}")
            return False
        
    def update_race(self, league_id, race_id, name, date_time, writer_uid):
        """Updates the basic metadata (name, date, writer) of an existing race."""
        if not league_id or not race_id:
            return False, "Missing league or race ID"

        try:
            # Use updateMask to ensure we ONLY overwrite these three fields
            # and don't accidentally erase start_list, status, or settings
            url = f"{self.db_url}/Leagues/{league_id}/Races/{race_id}?updateMask.fieldPaths=name&updateMask.fieldPaths=date_time&updateMask.fieldPaths=writer_uid"
            
            firestore_payload = {
                "fields": {
                    "name": {"stringValue": name},
                    "date_time": {"stringValue": date_time},
                    "writer_uid": {"stringValue": writer_uid}
                }
            }
            
            response = self._make_request("PATCH", url, json=firestore_payload)
            response.raise_for_status()
            
            self.log(f"Race '{name}' (ID: {race_id}) updated successfully.")
            return True, "Race updated successfully"
            
        except requests.exceptions.HTTPError as e:
            msg = f"HTTP Error updating race: {e.response.text}"
            self.log(msg)
            return False, msg
        except Exception as e:
            msg = f"Failed to update race: {str(e)}"
            self.log(msg)
            return False, msg
        
    def get_race(self, league_id, race_id):
        """Fetches the entire race document (settings, status, start_list)"""
        if not league_id or not race_id:
            return {}
            
        url = f"{self.db_url}/Leagues/{league_id}/Races/{race_id}"
        response = self._make_request("GET", url)
        
        if response and response.status_code == 200:
            doc_data = response.json()
            return self._parse_firestore_document(doc_data)
        else:
            self.log(f"[Warning] Failed to fetch race document. Status: {response.status_code if response else 'None'}")
            return {}
        
    def get_races_for_league(self, league_id):
        """Fetches all races for a specific league from the nested subcollection."""
        if not league_id:
            return []

        # Target the nested subcollection
        url = f"{self.db_url}/Leagues/{league_id}/Races"
        response = self._make_request("GET", url)
        races = []
        
        if response and response.status_code == 200:
            data = response.json()
            # Firestore returns a "documents" array if it found anything
            if "documents" in data:
                for doc in data["documents"]:
                    # The document ID is the last part of the document path
                    doc_path = doc.get("name", "")
                    doc_id = doc_path.split("/")[-1] 
                    
                    fields = doc.get("fields", {})
                    # Safely extract the name (fallback to doc_id if name field is missing)
                    race_name = fields.get("name", {}).get("stringValue", doc_id)
                    writer_uid = fields.get("writer_uid", {}).get("stringValue", "")
                    
                    # FIX: Extract the date_time field
                    date_time = fields.get("date_time", {}).get("stringValue", "")
                    
                    races.append({
                        "id": doc_id,
                        "name": race_name,
                        "writer_uid": writer_uid,
                        "date_time": date_time  # FIX: Add it to your returned dictionary
                    })
        else:
            self.log(f"[Warning] Failed to fetch races for league {league_id}. Status: {response.status_code if response else 'None'}")
            
        return races
    
    def get_race_start_list(self, league_id, race_id):
        """Fetches the start list array from the specific race document."""
        if not league_id or not race_id:
            return []
            
        # Target the document itself, NOT a subcollection
        url = f"{self.db_url}/Leagues/{league_id}/Races/{race_id}"
        response = self._make_request("GET", url)
        
        if response and response.status_code == 200:
            doc_data = response.json()
            # Use your existing parser to clean up the messy REST API format
            parsed_data = self._parse_firestore_document(doc_data)
            
            # Extract the array field
            start_list = parsed_data.get("start_list", [])
            return start_list
        else:
            self.log(f"[Warning] Failed to fetch start list. Status: {response.status_code if response else 'None'}")
            return []
        
    def update_race_start_list(self, league_id, race_id, start_list_data):
        """Updates the start list array in the race document."""
        try:
            url = f"{self.db_url}/Leagues/{league_id}/Races/{race_id}?updateMask.fieldPaths=start_list&updateMask.fieldPaths=status"
            
            firestore_payload = {
                "fields": {
                    "start_list": self._format_for_firestore(start_list_data),
                    "status": {"stringValue": "ready"}
                }
            }
            
            response = self._make_request("PATCH", url, json=firestore_payload)
            response.raise_for_status()
            
            self.log(self._t("race_published"))
            return True, self._t("race_published")
            
        except Exception as e:
            msg = self._t("err_db_update", error=str(e))
            self.log(msg)
            return False, msg
        
    def update_race_data(self, league_id, race_id, start_list_data, race_settings):
        """Updates both the start list array and the race settings in the race document."""
        try:
            # We use updateMask to tell Firestore exactly which fields we are updating
            # so we don't accidentally overwrite the race name or date.
            url = f"{self.db_url}/Leagues/{league_id}/Races/{race_id}?updateMask.fieldPaths=start_list&updateMask.fieldPaths=settings&updateMask.fieldPaths=status"
            
            firestore_payload = {
                "fields": {
                    "start_list": self._format_for_firestore(start_list_data),
                    "settings": self._format_for_firestore(race_settings),
                    "status": {"stringValue": "ready"}
                }
            }
            
            response = self._make_request("PATCH", url, json=firestore_payload)
            response.raise_for_status()
            
            self.log(self._t("race_published"))
            return True, self._t("race_published")
            
        except Exception as e:
            msg = self._t("err_db_update", error=str(e))
            self.log(msg)
            return False, msg
    
    def delete_user(self, user_uid):
        """Deletes a user account from Firestore."""
        try:
            url = f"{self.db_url}/Users/{user_uid}"
            response = self._make_request("DELETE", url)
            response.raise_for_status()
            self.log(f"User {user_uid} deleted successfully")
            return True, f"User deleted successfully"
        except Exception as e:
            msg = f"Failed to delete user: {str(e)}"
            self.log(msg)
            return False, msg
    
    def complete_race(self, league_id, race_id, race_name):
        """Marks race as completed and sends FCM notification."""
        try:
            # Update race status to "completed"
            url = f"{self.db_url}/Leagues/{league_id}/Races/{race_id}?updateMask.fieldPaths=status"
            
            firestore_payload = {
                "fields": {
                    "status": {"stringValue": "completed"}
                }
            }
            
            response = self._make_request("PATCH", url, json=firestore_payload)
            response.raise_for_status()
            
            # Send FCM notification
            topic_race = f"race_{league_id}_{race_id}".replace(" ", "_")
            topic_league = f"league_{league_id}".replace(" ", "_")
            
            try:
                import firebase_admin
                from firebase_admin import messaging
                
                if not firebase_admin._apps:
                    import os
                    from firebase_admin import credentials
                    cred_path = os.getenv('FIREBASE_KEY_PATH')
                    if cred_path and os.path.exists(cred_path):
                        cred = credentials.Certificate(cred_path)
                        firebase_admin.initialize_app(cred)
                
                # Send to race topic
                msg_race = messaging.Message(
                    data={
                        "type": "race_complete",
                        "raceId": race_id,
                        "leagueId": league_id,
                        "raceName": race_name,
                    },
                    topic=topic_race,
                )
                messaging.send(msg_race)
                
                # Send to league topic
                msg_league = messaging.Message(
                    data={
                        "type": "race_complete",
                        "raceId": race_id,
                        "leagueId": league_id,
                        "raceName": race_name,
                    },
                    topic=topic_league,
                )
                messaging.send(msg_league)
                
                self.log(f"Race {race_name} completed with notifications sent")
            except Exception as notif_error:
                self.log(f"Warning: Notification failed but race marked complete: {notif_error}")
            
            return True, f"Race '{race_name}' completed successfully!"
            
        except Exception as e:
            msg = f"Failed to complete race: {str(e)}"
            self.log(msg)
            return False, msg

    # This function calls the Cloud Function to send a push notification about the attempt result
    def trigger_push_notification(self, race_id, league_id, team_name, reason_key, is_np, title_key):
        # Replace with the actual URL Firebase gave you
        function_url = "https://europe-west3-mma-project-91699.cloudfunctions.net/send_run_notification"
        
        payload = {
            "raceId": race_id,
            "leagueId": league_id,
            "teamName": team_name,
            "resultValue": reason_key,
            "isNP": is_np,
            "titleKey": title_key
        }
        
        try:
            response = requests.post(function_url, json=payload)
            if response.status_code == 200:
                print(f"Push notification sent successfully for {team_name}!")
            else:
                print(f"Failed to send push: {response.text}")
        except Exception as e:
            print(f"Error calling Cloud Function: {e}")