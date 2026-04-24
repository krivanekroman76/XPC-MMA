import 'dart:async';
import 'package:flutter/material.dart';
import 'package:firebase_database/firebase_database.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'team_model.dart';
import 'home_screen.dart';

// Key for global Snackbar access
final GlobalKey<ScaffoldMessengerState> globalMessengerKey = GlobalKey<ScaffoldMessengerState>();

class FirebaseService {
  static final FirebaseService _instance = FirebaseService._internal();
  factory FirebaseService() => _instance;
  FirebaseService._internal();

  final DatabaseReference _db = FirebaseDatabase.instance.ref();
  final FirebaseMessaging _fcm = FirebaseMessaging.instance;
  SharedPreferences? _prefs;
  GlobalKey<NavigatorState>? _navigatorKey;

  String? _currentFcmToken;
  List<String> currentRaces = [];
  bool _isInitialized = false;

  final String _vapidKey = "BIpgBBBkba1SAXvyuYC5ROVs6P2akxwHzcicNuq0SgKeIv2x5RqoBQKw7OCcocNOjSzMbePIuvzIeGmWDLRqGus";

  void setNavigatorKey(GlobalKey<NavigatorState> key) {
    _navigatorKey = key;
  }

  void navigateToRace(String raceName) {
    _navigatorKey?.currentState?.push(
      MaterialPageRoute(builder: (context) => RaceLeaderboard(initialRace: raceName)),
    );
  }

  Future<bool> init() async {
    _prefs ??= await SharedPreferences.getInstance();
    if (_currentFcmToken != null) return true;

    try {
      NotificationSettings settings = await _fcm.requestPermission(
        alert: true,
        badge: true,
        sound: true,
      );
      
      if (settings.authorizationStatus == AuthorizationStatus.authorized) {
        _currentFcmToken = await _fcm.getToken(vapidKey: _vapidKey);

        if (_currentFcmToken != null) {
          debugPrint("FCM TOKEN: $_currentFcmToken");
          _syncAllSubscriptions();

          if (!_isInitialized) {
            _fcm.onTokenRefresh.listen((newToken) {
              _currentFcmToken = newToken;
              _syncAllSubscriptions();
            });

            FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) {
              String? raceName = message.data['raceName'];
              if (raceName != null) navigateToRace(raceName);
            });

            FirebaseMessaging.onMessage.listen((RemoteMessage message) {
              _handleForegroundMessage(message);
            });
            _isInitialized = true;
          }
          return true;
        }
      }
    } catch (e) {
      debugPrint("FCM Init Error: $e");
    }
    return false;
  }

  void _handleForegroundMessage(RemoteMessage message) {
    String? raceName = message.data['raceName'];
    if (isMasterNotificationEnabled || (raceName != null && isRaceNotificationEnabled(raceName))) {
      bool isNP = message.data['isNP'] == 'true';
      bool isBetter = message.data['isBetter'] == 'true';
      String msg = message.data['msg'] ?? message.notification?.body ?? '';

      globalMessengerKey.currentState?.removeCurrentSnackBar();
      globalMessengerKey.currentState?.showSnackBar(
        SnackBar(
          content: InkWell(
            onTap: () {
              if (raceName != null) navigateToRace(raceName);
              globalMessengerKey.currentState?.hideCurrentSnackBar();
            },
            child: Row(
              children: [
                Icon(
                  isNP ? Icons.cancel : (isBetter ? Icons.local_fire_department : Icons.timer),
                  color: Colors.white,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    msg,
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14),
                  ),
                ),
                if (raceName != null) const Icon(Icons.open_in_new, color: Colors.white70, size: 20),
              ],
            ),
          ),
          backgroundColor: isNP ? Colors.grey.shade800 : (isBetter ? Colors.green.shade600 : Colors.blue.shade600),
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          duration: const Duration(seconds: 5),
        ),
      );
    }
  }

  void _syncAllSubscriptions() {
    if (_currentFcmToken == null || _prefs == null) return;
    final keys = _prefs!.getKeys();
    for (String key in keys) {
      if (key.startsWith('notify_') && _prefs!.getBool(key) == true) {
        String topic = key.replaceFirst('notify_', '');
        _db.child('subscribers/$topic/$_currentFcmToken').set(true);
      }
    }
    if (isMasterNotificationEnabled) {
      _db.child('subscribers/all_races/$_currentFcmToken').set(true);
    }
  }

  bool get isMasterNotificationEnabled => _prefs?.getBool('master_notifications') ?? false;

  Future<void> setMasterNotification(bool enable) async {
    await _prefs?.setBool('master_notifications', enable);
    if (_currentFcmToken != null) {
      if (enable) {
        await _db.child('subscribers/all_races/$_currentFcmToken').set(true);
        final keys = _prefs!.getKeys();
        for (String key in keys) {
          if (key.startsWith('notify_') && _prefs!.getBool(key) == true) {
            String topic = key.replaceFirst('notify_', '');
            await _db.child('subscribers/$topic/$_currentFcmToken').remove();
            await _prefs!.setBool(key, false);
          }
        }
      } else {
        await _db.child('subscribers/all_races/$_currentFcmToken').remove();
      }
    }
  }

  bool isRaceNotificationEnabled(String raceName) {
    String topic = _formatTopicName(raceName);
    return _prefs?.getBool('notify_$topic') ?? false;
  }

  Future<void> setRaceNotification(String raceName, bool enable) async {
    String topic = _formatTopicName(raceName);
    await _prefs?.setBool('notify_$topic', enable);
    if (_currentFcmToken != null) {
      if (enable) {
        await _db.child('subscribers/$topic/$_currentFcmToken').set(true);
      } else {
        await _db.child('subscribers/$topic/$_currentFcmToken').remove();
      }
    }
  }

  String _formatTopicName(String name) => name.replaceAll(' ', '_').replaceAll(RegExp(r'[^a-zA-Z0-9_]'), '');

  Stream<List<String>> getRacesStream() {
    return _db.child('races').onValue.map((event) {
      if (event.snapshot.value == null) return [];
      final data = Map<dynamic, dynamic>.from(event.snapshot.value as Map);
      return data.keys.where((k) => k != 'current_race').map((e) => e.toString()).toList()..sort();
    });
  }

  Stream<RaceSettings> getSettingsStream(String raceName) {
    String formattedRaceName = raceName.replaceAll(' ', '_');
    return _db.child('races/$formattedRaceName/settings').onValue.map((event) {
      if (event.snapshot.value == null) return RaceSettings.defaultSettings();
      final map = Map<String, dynamic>.from(event.snapshot.value as Map);
      return RaceSettings.fromJson(map);
    });
  }

  Stream<List<Team>> getTeamsStream(String raceName, String category) {
    String formattedRaceName = raceName.replaceAll(' ', '_');
    return _db.child('races/$formattedRaceName/$category').onValue.map((event) {
      if (event.snapshot.value == null) return <Team>[];
      List<Team> teams = [];
      dynamic rawValue = event.snapshot.value;
      if (rawValue is Map) {
        rawValue.forEach((key, value) {
          if (value is Map) teams.add(Team.fromFirebase(key.toString(), value, fallbackCategory: category));
        });
      }
      teams.sort((a, b) => (a.startNo).compareTo(b.startNo));
      return teams;
    });
  }
}
