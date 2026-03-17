import 'package:firebase_database/firebase_database.dart';
import 'package:flutter/material.dart';
import 'dart:async';
import 'team_model.dart';

class FirebaseService {
  static final FirebaseService _instance = FirebaseService._internal();
  factory FirebaseService() => _instance;
  FirebaseService._internal();

  final FirebaseDatabase _db = FirebaseDatabase.instance;

  List<String> _cachedRaces = [];
  final _racesController = StreamController<List<String>>.broadcast();
  StreamSubscription? _racesSubscription;
  StreamSubscription? _globalRaceSubscription;

  // Internal notification stream for reliable popups
  final _notificationController = StreamController<Map<String, dynamic>>.broadcast();
  Stream<Map<String, dynamic>> get notifications => _notificationController.stream;

  final Map<String, int> _lastAttemptCounts = {};
  final Map<String, int> _lastKnownBestTimes = {};

  List<String> get currentRaces => _cachedRaces;

  void init() {
    if (_racesSubscription != null) return;
    _racesSubscription = _db.ref('races').onValue.listen((event) {
      final data = event.snapshot.value as Map?;
      if (data != null) {
        _cachedRaces = data.keys
            .where((k) => data[k] is Map && k != 'current_race')
            .map((e) => e.toString())
            .toList()..sort();
      } else {
        _cachedRaces = [];
      }
      _racesController.add(_cachedRaces);
    });
  }

  Stream<List<String>> getRacesStream() {
    init();
    if (_cachedRaces.isNotEmpty) {
      Timer.run(() => _racesController.add(_cachedRaces));
    }
    return _racesController.stream;
  }

  Stream<String> getRaceStatusStream(String raceName) {
    return _db.ref('races/$raceName').onValue.map((event) {
      final data = event.snapshot.value as Map?;
      if (data == null) return "running";

      final complete = data['complete'] as Map?;
      final raceStatus = complete?['race_status'] as Map?;
      if (raceStatus?['is_finished'] == true) {
        return "finished";
      }

      return data['status']?.toString() ?? "running";
    });
  }

  void startMonitoringRace(String raceName) {
    _globalRaceSubscription?.cancel();
    _lastAttemptCounts.clear();
    _lastKnownBestTimes.clear();

    _globalRaceSubscription = _db.ref('races/$raceName').onValue.listen((event) {
      final data = event.snapshot.value as Map?;
      if (data == null) return;

      data.forEach((catKey, catValue) {
        if (catValue is Map && catKey != 'complete' && catKey != 'status' && catKey != 'leaderboard') {
          catValue.forEach((teamKey, teamValue) {
            if (teamValue is Map) {
              final team = Team.fromFirebase(teamKey.toString(), Map<String, dynamic>.from(teamValue), fallbackCategory: catKey);
              _checkAndNotify(raceName, catKey, team);
            }
          });
        }
      });
    });
  }

  void _checkAndNotify(String raceName, String category, Team team) {
    String storageKey = "${raceName}_${category}_${team.id}";
    int currentAttemptCount = team.attempts.length;

    if (!_lastAttemptCounts.containsKey(storageKey)) {
      _lastAttemptCounts[storageKey] = currentAttemptCount;
      _lastKnownBestTimes[storageKey] = team.bestTime;
      return;
    }

    int lastAttemptCount = _lastAttemptCounts[storageKey] ?? 0;

    if (currentAttemptCount > lastAttemptCount) {
      final newAttempt = team.attempts.last;
      if (newAttempt is Map) {
        int newTime = Team.parseTime(newAttempt['final_time'] ?? newAttempt['finalTime']);
        int previousBest = _lastKnownBestTimes[storageKey] ?? 0;
        
        bool isBetter = previousBest == 0 || (newTime > 0 && newTime < previousBest);
        bool isNP = newTime >= 999999;

        _notificationController.add({
          'teamName': team.name,
          'category': category,
          'time': Team.formatMs(newTime),
          'isBetter': isBetter,
          'isNP': isNP,
        });
      }
    }

    _lastAttemptCounts[storageKey] = currentAttemptCount;
    if (team.bestTime > 0) {
      _lastKnownBestTimes[storageKey] = team.bestTime;
    }
  }

  Stream<List<Team>> getTeamsStream(String raceName, String category) {
    return _db.ref('races/$raceName/$category').onValue.map((event) {
      final data = event.snapshot.value as Map?;
      if (data == null) return [];
      List<Team> teams = [];
      data.forEach((key, value) {
        if (key != 'leaderboard' && key != 'status' && value is Map) {
          teams.add(Team.fromFirebase(key.toString(), Map<String, dynamic>.from(value), fallbackCategory: category));
        }
      });
      return teams;
    });
  }
}
