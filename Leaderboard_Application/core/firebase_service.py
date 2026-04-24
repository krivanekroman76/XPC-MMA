import requests
import json
import urllib.parse # Make sure this is imported at the top of your file
    
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
            with open('firebase-config.json') as f:
                config = json.load(f)
                
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
        try:
            with open(f'{self.language}.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"[Warning] Translation file {self.language}.json not found. Falling back to keys.")
            return {}

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

    def _refresh_id_token(self):
        """Automatically refreshes the Auth token when it expires."""
        if not hasattr(self, 'refresh_token') or not self.refresh_token:
            return False
        url = f"https://securetoken.googleapis.com/v1/token?key={self.api_key}"
        payload = {"grant_type": "refresh_token", "refresh_token": self.refresh_token}
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            self.id_token = data['id_token']
            self.refresh_token = data['refresh_token']
            return True
        except:
            return False

    def _get_headers(self):
        """Returns authorization headers for requests."""
        if not self.id_token: return {}
        return {"Authorization": f"Bearer {self.id_token}"}

    def _make_request(self, method, url, **kwargs):
        """Smart wrapper for Firestore API, handles token injection and refresh."""
        headers = self._get_headers()
        if 'headers' in kwargs:
            headers.update(kwargs['headers'])
        kwargs['headers'] = headers

        response = requests.request(method, url, **kwargs)
        
        if response.status_code == 401:
            self.log(self._t("token_expired"))
            if self._refresh_id_token():
                kwargs['headers'] = self._get_headers()
                response = requests.request(method, url, **kwargs)
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
        