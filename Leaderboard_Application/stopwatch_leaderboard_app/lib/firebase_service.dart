import 'package:cloud_firestore/cloud_firestore.dart';
import 'team_model.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter/material.dart';

class FirebaseService {
  static final FirebaseService _instance = FirebaseService._internal();
  factory FirebaseService() => _instance;
  FirebaseService._internal();

  final FirebaseFirestore _db = FirebaseFirestore.instance;

  GlobalKey<NavigatorState>? _navigatorKey;

  void setNavigatorKey(GlobalKey<NavigatorState> key) {
    _navigatorKey = key;
  }

  bool isMasterNotificationEnabled = false;
  List<String> _subscribedRaces = [];

  Future<bool> init() async {
    final prefs = await SharedPreferences.getInstance();
    _subscribedRaces = prefs.getStringList('subscribed_races') ?? [];
    return true;
  }

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
      // Extract the 'settings' map from the document
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

      // 1. Get document data as a Map
      final data = snapshot.data() as Map<String, dynamic>;

      // 2. Get the raw start_list
      final rawStartList = data['start_list'];

      // 3. Safe parsing: convert List to Map if necessary
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

      // 4. Create the list of teams
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

  // --- NOTIFICATIONS LOGIC ---
  static const String _prefKey = "subscribed_topics";
  List<String> _subscribedIds = [];
  bool isMasterOn = false; // "Global" switch

  Future<void> initNotifications() async {
    SharedPreferences prefs = await SharedPreferences.getInstance();
    _subscribedIds = prefs.getStringList(_prefKey) ?? [];
    isMasterOn = prefs.getBool("master_notif") ?? false;
  }

  bool isRaceNotificationEnabled(String raceId) {
    if (isMasterOn) return true; // Global overrides local
    return _subscribedIds.contains(raceId);
  }

  Future<void> toggleMasterNotification(String leagueId, bool enable) async {
    isMasterOn = enable;
    SharedPreferences prefs = await SharedPreferences.getInstance();
    await prefs.setBool("master_notif", enable);

    if (enable) {
      await FirebaseMessaging.instance.subscribeToTopic("league_$leagueId");
    } else {
      await FirebaseMessaging.instance.unsubscribeFromTopic("league_$leagueId");
    }
  }

  Future<void> setRaceNotification(String leagueId, String raceId, bool enable) async {
    String topic = "race_${leagueId}_$raceId";
    SharedPreferences prefs = await SharedPreferences.getInstance();

    if (enable) {
      _subscribedIds.add(raceId);
      await FirebaseMessaging.instance.subscribeToTopic(topic);
    } else {
      _subscribedIds.remove(raceId);
      await FirebaseMessaging.instance.unsubscribeFromTopic(topic);
    }

    await prefs.setStringList(_prefKey, _subscribedIds);
  }

  // --- OVER THE AIR (OTA) TRANSLATIONS LOGIC ---

  // Fetches the 'metadata' document to see which languages exist and their versions
  Future<Map<String, dynamic>> getTranslationVersions() async {
    try {
      final doc = await _db.collection('Translations').doc('metadata').get();
      return doc.data() ?? {};
    } catch (e) {
      print("Error fetching translation versions: $e");
      return {};
    }
  }

  // Downloads the actual dictionary for a specific language (e.g., 'en' or 'de')
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