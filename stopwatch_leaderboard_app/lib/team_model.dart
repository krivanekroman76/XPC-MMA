import 'package:flutter/foundation.dart';

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
        ..sort((a, b) => int.parse(a.toString()).compareTo(int.parse(b.toString())));
      attempts = sortedKeys.map((k) => rawAttempts[k]).toList();
    }

    if (extractedBestTime == 0 && attempts.isNotEmpty) {
      for (var attempt in attempts) {
        if (attempt is Map) {
          int ft = parseTime(attempt['final_time'] ?? attempt['finalTime']);
          if (ft > 0 && (extractedBestTime == 0 || ft < extractedBestTime)) {
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
    if (ms == 0) return "--:--";
    if (ms >= 999999) return "NP";
    return "${(ms / 1000).toStringAsFixed(2)}s";
  }

  String getRunLaneTime(int runIndex, int laneIndex) {
    if (attempts.length <= runIndex) return "--";
    final run = attempts[runIndex];
    if (run is Map && run['lanes'] != null) {
      final lanesData = run['lanes'];
      dynamic laneValue;

      if (lanesData is List) {
        if (laneIndex < lanesData.length) {
          laneValue = lanesData[laneIndex];
        }
      } else if (lanesData is Map) {
        laneValue = lanesData[laneIndex.toString()] ?? lanesData[laneIndex];
      }

      if (laneValue == null || laneValue == 0) return "--";
      
      int timeMs = parseTime(laneValue);
      if (timeMs >= 999999) return "NP";
      return (timeMs / 1000).toStringAsFixed(2);
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
