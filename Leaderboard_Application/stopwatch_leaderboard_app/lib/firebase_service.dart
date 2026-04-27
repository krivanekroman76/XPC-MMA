import 'package:flutter/foundation.dart'; // REQUIRED to check if running on Web/PWA
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter/material.dart';
import 'team_model.dart';

class FirebaseService {
  static final FirebaseService _instance = FirebaseService._internal();
  factory FirebaseService() => _instance;
  FirebaseService._internal();

  final FirebaseFirestore _db = FirebaseFirestore.instance;

  GlobalKey<NavigatorState>? _navigatorKey;

  void setNavigatorKey(GlobalKey<NavigatorState> key) {
    _navigatorKey = key;
  }

  // --- DATA STREAMS ---

  // 1. Get Leagues Stream
  Stream<List<String>> getLeaguesStream() {
    return _db.collection('Leagues').snapshots().map((snapshot) {
      return snapshot.docs.map((doc) => doc.id).toList();
    });
  }

  // 2. Get Races for a Specific League
  Stream<List<String>> getRacesStream(String leagueId) {
    return _db.collection('Leagues').doc(leagueId).collection('Races').snapshots().map((snapshot) {
      return snapshot.docs.map((doc) => doc.id).toList();
    });
  }

  // 3. Get Settings Stream for a Race
  Stream<RaceSettings> getSettingsStream(String league, String race) {
    return _db.collection('Leagues').doc(league).collection('Races').doc(race).snapshots().map((snapshot) {
      if (!snapshot.exists || snapshot.data() == null) return RaceSettings.defaultSettings();

      final data = snapshot.data()!;
      final settingsData = data['settings'] as Map<String, dynamic>?;
      return RaceSettings.fromMap(settingsData);
    });
  }

  // 4. Get Teams Stream for a Race (Filtered by Category)
  Stream<List<Team>> getTeamsStream(String league, String race, String category) {
    return _db
        .collection('Leagues')
        .doc(league)
        .collection('Races')
        .doc(race)
        .snapshots()
        .map((snapshot) {
      if (!snapshot.exists || snapshot.data() == null) return <Team>[];

      final data = snapshot.data() as Map<String, dynamic>;
      final rawStartList = data['start_list'];

      Map<String, dynamic> startListMap = {};

      if (rawStartList is List) {
        for (int i = 0; i < rawStartList.length; i++) {
          if (rawStartList[i] != null && rawStartList[i] is Map) {
            startListMap[i.toString()] = rawStartList[i] as Map<String, dynamic>;
          }
        }
      } else if (rawStartList is Map) {
        startListMap = Map<String, dynamic>.from(rawStartList);
      }

      List<Team> teams = [];

      startListMap.forEach((key, value) {
        try {
          final teamData = value as Map<String, dynamic>;
          final teamCat = teamData['category']?.toString() ?? '';

          if (category == "Vše" || teamCat == category) {
            teams.add(Team.fromFirestore(key, teamData));
          }
        } catch (e) {
          print("!!! ERROR PARSING TEAM WITH KEY '$key': $e");
        }
      });

      return teams;
    });
  }

  // --- NOTIFICATIONS LOGIC (HYBRID: TOPICS + TOKENS) ---

  static const String _prefKey = "subscribed_topics";
  List<String> _subscribedIds = [];
  bool isMasterOn = false;

  Future<void> initNotifications() async {
    SharedPreferences prefs = await SharedPreferences.getInstance();
    _subscribedIds = prefs.getStringList(_prefKey) ?? [];
    isMasterOn = prefs.getBool("master_notif") ?? false;
  }

  bool isRaceNotificationEnabled(String raceId) {
    if (isMasterOn) return true;
    return _subscribedIds.contains(raceId);
  }

  // Helper method to get the current language from SharedPreferences
  Future<String> _getCurrentLanguage() async {
    SharedPreferences prefs = await SharedPreferences.getInstance();
    return prefs.getString('selected_language') ?? 'cs'; // Default to 'cs' if not found
  }

// --- UPDATED: TOKEN-ONLY NOTIFICATIONS ---

  Future<void> toggleMasterNotification(String leagueId, bool enable) async {
    isMasterOn = enable;
    SharedPreferences prefs = await SharedPreferences.getInstance();
    await prefs.setBool("master_notif", enable);

    String lang = await _getCurrentLanguage();

    // REMOVED kIsWeb check and Topics.
    // Now EVERY platform saves its token to Firestore.
    await _updateFirestoreToken(leagueId: leagueId, subscribe: enable, lang: lang);
  }

  Future<void> setRaceNotification(String leagueId, String raceId, bool enable) async {
    SharedPreferences prefs = await SharedPreferences.getInstance();
    String lang = await _getCurrentLanguage();

    if (enable) {
      if (!_subscribedIds.contains(raceId)) _subscribedIds.add(raceId);
    } else {
      _subscribedIds.remove(raceId);
    }
    await prefs.setStringList(_prefKey, _subscribedIds);

    // REMOVED kIsWeb check and Topics.
    // Now EVERY platform saves its token to Firestore.
    await _updateFirestoreToken(raceId: raceId, subscribe: enable, lang: lang);
  }
  
  // Private helper to handle Firestore token writing for Web/iOS-PWA
  Future<void> _updateFirestoreToken({String? raceId, String? leagueId, required bool subscribe, required String lang}) async {
    try {
      // NOTE: For Web, you MUST provide your VAPID key from Firebase Project Settings -> Cloud Messaging
      String? token = await FirebaseMessaging.instance.getToken(
          vapidKey: "BIpgBBBkba1SAXvyuYC5ROVs6P2akxwHzcicNuq0SgKeIv2x5RqoBQKw7OCcocNOjSzMbePIuvzIeGmWDLRqGus" // <--- REPLACE THIS WITH YOUR WEB VAPID KEY
      );

      if (token == null) return;

      final docRef = _db.collection('UserTokens').doc(token);

      if (subscribe) {
        Map<String, dynamic> updateData = {
          'token': token,
          'language': lang,
          'last_updated': FieldValue.serverTimestamp(),
        };

        if (raceId != null) {
          updateData['subscribed_races'] = FieldValue.arrayUnion([raceId]);
        }
        if (leagueId != null) {
          updateData['subscribed_leagues'] = FieldValue.arrayUnion([leagueId]);
        }

        await docRef.set(updateData, SetOptions(merge: true));
      } else {
        Map<String, dynamic> removeData = {};
        if (raceId != null) {
          removeData['subscribed_races'] = FieldValue.arrayRemove([raceId]);
        }
        if (leagueId != null) {
          removeData['subscribed_leagues'] = FieldValue.arrayRemove([leagueId]);
        }

        if (removeData.isNotEmpty) {
          await docRef.update(removeData);
        }
      }
    } catch (e) {
      print("Error updating Firestore token: $e");
    }
  }

  // --- OVER THE AIR (OTA) TRANSLATIONS LOGIC ---

  Future<Map<String, dynamic>> getTranslationVersions() async {
    try {
      final doc = await _db.collection('Translations').doc('metadata').get();
      return doc.data() ?? {};
    } catch (e) {
      print("Error fetching translation versions: $e");
      return {};
    }
  }

  Future<Map<String, dynamic>> downloadLanguageData(String langCode) async {
    try {
      final doc = await _db.collection('Translations').doc(langCode).get();
      return doc.data() ?? {};
    } catch (e) {
      print("Error downloading language $langCode: $e");
      return {};
    }
  }
}