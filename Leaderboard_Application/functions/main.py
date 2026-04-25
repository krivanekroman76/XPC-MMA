from firebase_functions import firestore_fn
from firebase_admin import initialize_app, messaging

# Initialize the Admin SDK natively on Google's servers
initialize_app() 

@firestore_fn.on_document_updated(document="Leagues/{leagueId}/Races/{raceId}")
def notify_on_race_published(event: firestore_fn.Event[firestore_fn.Change[firestore_fn.DocumentSnapshot]]) -> None:
    """
    Listens for updates to any Race document. If the status changes to "ready",
    it sends an FCM push notification to both Global (league) and Local (race) subscribers.
    """
    
    # Get the data before and after the update
    old_data = event.data.before.to_dict() if event.data.before else {}
    new_data = event.data.after.to_dict() if event.data.after else {}

    old_status = old_data.get("status")
    new_status = new_data.get("status")

    # Only trigger if the status was changed TO "ready" from something else
    if old_status != "ready" and new_status == "ready":
        race_name = new_data.get("name", "A new race")
        league_id = event.params["leagueId"]
        race_id = event.params["raceId"]

        print(f"Triggering notification for {race_name} (ID: {race_id}) in League: {league_id}")

        try:
            # 1. Define the topics
            topic_race = f"race_{league_id}_{race_id}"
            topic_league = f"league_{league_id}"
            
            # 2. Use a condition: This sends the notification to anyone who is 
            # subscribed to the WHOLE league OR just THIS specific race.
            # If they are subscribed to both, FCM is smart enough to only deliver it once.
            condition = f"'{topic_race}' in topics || '{topic_league}' in topics"

            message = messaging.Message(
                notification=messaging.Notification(
                    title="New Race Published! 🏁",
                    body=f"The start list for {race_name} is now available.",
                ),
                condition=condition
            )
            
            # 3. Send the message
            messaging.send(message)
            print(f"Successfully sent notification using condition: {condition}")
            
        except Exception as e:
            print(f"Error sending notification: {e}")