from firebase_functions import https_fn
from firebase_admin import initialize_app, firestore, messaging
import json

# Initialize the Firebase Admin SDK
initialize_app()

@https_fn.on_request()
def send_np_notification(req: https_fn.Request) -> https_fn.Response:
    # 1. Only accept POST requests
    if req.method != "POST":
        return https_fn.Response("Method Not Allowed", status=405)

    try:
        # Parse the JSON payload sent from your Admin tool
        request_data = req.get_json()
        if not request_data:
            return https_fn.Response(json.dumps({"error": "Empty payload"}), status=400, mimetype="application/json")

        race_id = request_data.get("raceId")
        league_id = request_data.get("leagueId", "") 
        team_name = request_data.get("teamName")
        reason_key = request_data.get("reasonKey")

        if not race_id or not team_name or not reason_key:
            return https_fn.Response(json.dumps({"error": "Missing parameters"}), status=400, mimetype="application/json")

        db = firestore.client()
        
        # ==========================================
        # 1. DYNAMICALLY FETCH ALL LANGUAGES
        # ==========================================
        supported_langs = []
        dicts = {}
        
        # Stream all documents in the Translations collection
        translations_docs = db.collection("Translations").stream()
        for doc in translations_docs:
            if doc.id != "metadata": 
                supported_langs.append(doc.id)
                dicts[doc.id] = doc.to_dict()
                
        # Grab the English dictionary for our fallback
        en_dict = dicts.get("en", {})
        
        # ==========================================
        # 2. FETCH TOKENS & GROUP DYNAMICALLY
        # ==========================================
        tokens_by_lang = {lang: [] for lang in supported_langs}
        token_docs = {} 
        processed_tokens = set() # Prevent sending duplicate notifications

        # Query 1: Users subscribed to the specific race
        race_query = db.collection("UserTokens").where("subscribed_races", "array_contains", race_id).stream()
        
        # Query 2: Users subscribed to the master league
        league_query = db.collection("UserTokens").where("subscribed_leagues", "array_contains", league_id).stream()

        def process_token_docs(docs_stream):
            for doc in docs_stream:
                data = doc.to_dict()
                token = data.get("token")
                
                if not token or token in processed_tokens:
                    continue
                    
                processed_tokens.add(token)
                
                lang = data.get("language", "en")
                if lang not in supported_langs:
                    lang = "en"

                tokens_by_lang[lang].append(token)
                token_docs[token] = doc.id

        # Run both queries
        process_token_docs(race_query)
        process_token_docs(league_query)

        # ==========================================
        # 3. TRANSLATE WITH CASCADING FALLBACK & SEND
        # ==========================================
        for lang in supported_langs:
            tr = dicts.get(lang, {})
            
            def get_text(key, default_fallback):
                if key in tr and tr[key]:               
                    return tr[key]
                elif key in en_dict and en_dict[key]:   
                    return en_dict[key]
                else:                                   
                    return default_fallback
            
            title = get_text("invalid_attempt", "Invalid Attempt")
            
            if reason_key.startswith("reason_"):
                reason_text = get_text(reason_key, reason_key)
            else:
                reason_text = reason_key 
                
            body = f"{team_name}: {reason_text}"

            notification_data = {
                "click_action": "FLUTTER_NOTIFICATION_CLICK",
                "leagueId": league_id,
                "raceId": race_id
            }

            # --- STEP A: Send to Native Android (Topics) ---
            # EXACT match to the Flutter subscription logic!
            #base_topic = f"race_{league_id}_{race_id}".replace(" ", "_")
            #topic_message = messaging.Message(
            #    notification=messaging.Notification(title=title, body=body),
            #    data=notification_data, 
            #    topic=base_topic
            #)
            #try:
            #    messaging.send(topic_message)
            #    print(f"Successfully sent to topic: {base_topic}")
            #except Exception as e:
            #    print(f"Topic send failed for {base_topic}: {e}")

            # --- STEP B: Send to Web / iOS PWA (Tokens) ---
            tokens = tokens_by_lang[lang]
            if tokens:
                token_message = messaging.MulticastMessage(
                    notification=messaging.Notification(title=title, body=body),
                    data=notification_data, 
                    tokens=tokens
                )
                
                response = messaging.send_each_for_multicast(token_message)
                
                # --- STEP C: Clean up dead tokens ---
                if response.failure_count > 0:
                    for idx, resp in enumerate(response.responses):
                        if not resp.success:
                            err_code = resp.exception.code if resp.exception else ""
                            if err_code in ['messaging/invalid-registration-token', 'messaging/registration-token-not-registered']:
                                bad_token = tokens[idx]
                                doc_id = token_docs[bad_token]
                                db.collection("UserTokens").doc(doc_id).delete()
                                print(f"Deleted dead token: {doc_id}")

        return https_fn.Response(json.dumps({"success": True}), status=200, mimetype="application/json")

    except Exception as e:
        print(f"Function error: {e}")
        return https_fn.Response(json.dumps({"error": str(e)}), status=500, mimetype="application/json")