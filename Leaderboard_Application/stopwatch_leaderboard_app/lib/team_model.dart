import 'package:flutter/foundation.dart';

class RaceSettings {
  final int attemptsCount;
  final int lanesCount;
  final bool isFinished;

  RaceSettings({
    required this.attemptsCount,
    required this.lanesCount,
    required this.isFinished,
  });

  factory RaceSettings.fromJson(Map<String, dynamic> json) {
    return RaceSettings(
      // Využíváme operátor ?? pro případ, že hodnota v databázi ještě není
      lanesCount: json['lanes_count'] ?? json['lanesCount'] ?? 2,
      attemptsCount: json['attempts_count'] ?? json['attemptsCount'] ?? 1,
      isFinished: json['is_finished'] ?? json['isFinished'] ?? false,
    );
  }

  factory RaceSettings.defaultSettings() {
    return RaceSettings(attemptsCount: 1, lanesCount: 2, isFinished: false);
  }
}

class Team {
  final String id;
  final String name;
  final String category;
  final int startNo;
  final int bestTime;
  final String status;
  final List<dynamic> attempts;

  Team({
    required this.id,
    required this.name,
    required this.category,
    required this.startNo,
    required this.bestTime,
    required this.status,
    required this.attempts,
  });

  static int parseInt(dynamic value) {
    if (value == null) return 0;
    if (value is int) return value;
    if (value is double) return value.toInt();
    if (value is String) return int.tryParse(value) ?? 0;
    return 0;
  }

  static int parseTime(dynamic value) {
    if (value == null) return 0;
    if (value is int) return value;
    if (value is double) return value < 1000 ? (value * 1000).toInt() : value.toInt();
    if (value is String) {
      double? d = double.tryParse(value);
      if (d != null) return d < 1000 ? (d * 1000).toInt() : d.toInt();
    }
    return 0;
  }

  factory Team.fromFirebase(String id, Map<dynamic, dynamic> data, {String? fallbackCategory}) {
    int extractedBestTime = parseTime(data['best_time'] ?? data['bestTime'] ?? data['time']);
    
    List<dynamic> attempts = [];
    final rawAttempts = data['attempts'];
    if (rawAttempts is List) {
      attempts = rawAttempts;
    } else if (rawAttempts is Map) {
      var sortedKeys = rawAttempts.keys.toList()
        ..sort((a, b) {
          int? ia = int.tryParse(a.toString());
          int? ib = int.tryParse(b.toString());
          if (ia != null && ib != null) return ia.compareTo(ib);
          return a.toString().compareTo(b.toString());
        });
      attempts = sortedKeys.map((k) => rawAttempts[k]).toList();
    }

    if (extractedBestTime == 0 && attempts.isNotEmpty) {
      for (var attempt in attempts) {
        if (attempt is Map) {
          int ft = parseTime(attempt['final_time'] ?? attempt['finalTime']);
          if (ft > 0 && ft < 999999 && (extractedBestTime == 0 || ft < extractedBestTime)) {
            extractedBestTime = ft;
          }
        }
      }
    }

    return Team(
      id: id,
      name: (data['name'] ?? data['team_name'] ?? id).toString(),
      category: (data['category'] ?? data['cat'] ?? fallbackCategory ?? 'Nezadáno').toString(),
      startNo: parseInt(data['start_no'] ?? data['startNo'] ?? data['st_no']),
      bestTime: extractedBestTime,
      status: (data['status'] ?? 'preparing').toString(),
      attempts: attempts,
    );
  }

  String get formattedTime => formatMs(bestTime);

  static String formatMs(int ms) {
    if (ms <= 0) return "--:--";
    if (ms >= 999999) return "NP";
    return "${(ms / 1000).toStringAsFixed(2)}s";
  }

  String getRunLaneTime(int runIndex, int laneIndex) {
    if (attempts.length <= runIndex) return "--";
    final run = attempts[runIndex];
    if (run is Map) {
      if (run['lanes'] != null) {
        final lanesData = run['lanes'];
        dynamic laneValue;
        
        // Target is 1-based index for lookup (Lane 1 = key 1)
        int targetIdx = laneIndex + 1;

        if (lanesData is List) {
          // Check if list actually has a value at the target index
          if (targetIdx < lanesData.length && lanesData[targetIdx] != null && lanesData[targetIdx] != 0) {
            laneValue = lanesData[targetIdx];
          } 
          // Only fallback to index 0 if targetIdx 1 failed and index 0 is valid
          else if (laneIndex == 0 && lanesData.isNotEmpty && lanesData[0] != null && lanesData[0] != 0) {
            laneValue = lanesData[0];
          }
        } else if (lanesData is Map) {
          // Strict 1-based lookup first
          laneValue = lanesData[targetIdx.toString()] ?? lanesData[targetIdx];
          
          // Fallback to 0-based only if 1st lane and no 1st lane found
          if (laneValue == null && laneIndex == 0) {
            laneValue = lanesData["0"] ?? lanesData[0];
          }
        }
        
        if (laneValue != null) {
          int timeMs = parseTime(laneValue);
          if (timeMs > 0) return timeMs >= 999999 ? "NP" : (timeMs / 1000).toStringAsFixed(2);
        }
      }
      
      // Secondary fallback for flat attempt structure
      final possibleKeys = ["lane_${laneIndex + 1}", "lane${laneIndex + 1}", "l${laneIndex + 1}"];
      for (var key in possibleKeys) {
        if (run[key] != null) {
          int timeMs = parseTime(run[key]);
          if (timeMs > 0) return timeMs >= 999999 ? "NP" : (timeMs / 1000).toStringAsFixed(2);
        }
      }
    }
    return "--";
  }

  String getRunFinalTime(int runIndex) {
    if (attempts.length <= runIndex) return "--:--";
    final run = attempts[runIndex];
    if (run is Map) {
      final finalTime = run['final_time'] ?? run['finalTime'];
      int ft = parseTime(finalTime);
      return formatMs(ft);
    }
    return "--:--";
  }
}
