from firebase_functions import https_fn
from firebase_admin import initialize_app, firestore, messaging
import json

# Initialize the Firebase Admin SDK (if not already initialized elsewhere)
try:
    initialize_app()
except ValueError:
    pass # App already initialized

# Note: If you rename the function here, your webhook URL will change!
# To this (using Frankfurt as an example):
@https_fn.on_request(region="europe-west3")
def send_run_notification(req: https_fn.Request) -> https_fn.Response:
    if req.method != "POST":
        return https_fn.Response("Method Not Allowed", status=405)

    try:
        request_data = req.get_json()
        if not request_data:
            return https_fn.Response(json.dumps({"error": "Empty payload"}), status=400, mimetype="application/json")

        race_id = request_data.get("raceId")
        league_id = request_data.get("leagueId", "") 
        team_name = request_data.get("teamName")
        
        result_value = request_data.get("resultValue") 
        is_np = request_data.get("isNP", False) 
        
        # NEW: We extract the titleKey sent by your Python Gateway. 
        # If it's missing, we default to "invalid_attempt" or "valid_attempt".
        default_title = "invalid_attempt" if is_np else "valid_attempt"
        title_key = request_data.get("titleKey", default_title)

        if not race_id or not team_name or not result_value:
            return https_fn.Response(json.dumps({"error": "Missing parameters"}), status=400, mimetype="application/json")

        db = firestore.client()
        
        # 1. DYNAMICALLY FETCH ALL LANGUAGES
        supported_langs = []
        dicts = {}
        translations_docs = db.collection("Translations").stream()
        for doc in translations_docs:
            if doc.id != "metadata": 
                supported_langs.append(doc.id)
                dicts[doc.id] = doc.to_dict()
                
        en_dict = dicts.get("en", {})
        
        # 2. FETCH TOKENS & GROUP DYNAMICALLY
        tokens_by_lang = {lang: [] for lang in supported_langs}
        token_docs = {} 
        processed_tokens = set()

        race_query = db.collection("UserTokens").where("subscribed_races", "array_contains", race_id).stream()
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

        process_token_docs(race_query)
        process_token_docs(league_query)

        # 3. TRANSLATE AND BUILD NOTIFICATION
        for lang in supported_langs:
            tr = dicts.get(lang, {})
            
            def get_text(key, default_fallback):
                if key in tr and tr[key]:               
                    return tr[key]
                elif key in en_dict and en_dict[key]:   
                    return en_dict[key]
                else:                                   
                    return default_fallback
            
            # --- UPDATED TRANSLATION LOGIC ---
            # Translate the title dynamically based on the title_key from Python
            title = get_text(title_key, title_key)

            if is_np:
                # It's an Invalid Attempt, translate the reason string
                if str(result_value).startswith("reason_"):
                    display_text = get_text(result_value, result_value)
                else:
                    display_text = result_value 
            else:
                # It's a Valid Attempt, just append the seconds ('s') to the time
                display_text = f"{result_value} s" 
                
            body = f"{team_name}: {display_text}"
            # ---------------------------------

            notification_data = {
                "click_action": "FLUTTER_NOTIFICATION_CLICK",
                "leagueId": league_id,
                "raceId": race_id
            }

            tokens = tokens_by_lang[lang]
            if tokens:
                token_message = messaging.MulticastMessage(
                    notification=messaging.Notification(title=title, body=body),
                    data=notification_data, 
                    tokens=tokens
                )
                
                response = messaging.send_each_for_multicast(token_message)
                
                # Cleanup dead tokens
                if response.failure_count > 0:
                    for idx, resp in enumerate(response.responses):
                        if not resp.success:
                            err_code = resp.exception.code if resp.exception else ""
                            if err_code in ['messaging/invalid-registration-token', 'messaging/registration-token-not-registered']:
                                bad_token = tokens[idx]
                                doc_id = token_docs[bad_token]
                                db.collection("UserTokens").doc(doc_id).delete()

        return https_fn.Response(json.dumps({"success": True}), status=200, mimetype="application/json")

    except Exception as e:
        print(f"Function error: {e}")
        return https_fn.Response(json.dumps({"error": str(e)}), status=500, mimetype="application/json")