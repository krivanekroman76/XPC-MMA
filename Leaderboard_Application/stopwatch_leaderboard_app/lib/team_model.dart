class RaceSettings {
  final int attemptsCount;
  final int lanesCount;
  final int sectionsCount;
  final String logic;
  final bool isFinished;
  final List<String> runOrder; // ADD THIS

  RaceSettings({
    required this.attemptsCount,
    required this.lanesCount,
    required this.sectionsCount,
    required this.logic,
    required this.isFinished,
    required this.runOrder, // ADD THIS
  });

  factory RaceSettings.fromMap(Map<String, dynamic>? data) {
    if (data == null) return RaceSettings.defaultSettings();

    // Parse the run_order array safely
    List<String> parsedRunOrder = [];
    if (data['run_order'] is List) {
      parsedRunOrder = List<String>.from(data['run_order']);
    }

    return RaceSettings(
      attemptsCount: data['attempts'] ?? 2,
      lanesCount: data['lanes'] ?? 1,
      sectionsCount: data['sections'] ?? 1,
      logic: data['logic'] ?? 'standard',
      isFinished: data['isFinished'] ?? false,
      runOrder: parsedRunOrder, // ADD THIS
    );
  }

  static RaceSettings defaultSettings() => RaceSettings(
    attemptsCount: 2,
    lanesCount: 1,
    sectionsCount: 1,
    logic: 'standard',
    isFinished: false,
    runOrder: [], // ADD THIS
  );
}

class Team {
  final String id;
  final String name;
  final String category;
  final int startNo;
  final String status;
  final double bestTime;
  final List<dynamic> attempts; // Array from Firestore

  Team({
    required this.id,
    required this.name,
    required this.category,
    required this.startNo,
    required this.status,
    required this.bestTime,
    required this.attempts,
  });

  factory Team.fromFirestore(String key, Map<String, dynamic> data) {
    // Parse best_time safely (it might not exist or might be an int/double)
    double parsedBestTime = 999999.0;
    if (data['best_time'] != null) {
      parsedBestTime = (data['best_time'] is num)
          ? (data['best_time'] as num).toDouble()
          : double.tryParse(data['best_time'].toString()) ?? 999999.0;
    }

    return Team(
      id: key, // The "0", "1", "2" key from start_list
      name: data['team'] ?? 'Neznámý',
      category: data['category'] ?? 'Muži',
      startNo: data['start_no'] ?? 0,
      status: data['state'] ?? 'IDLE',
      bestTime: parsedBestTime,
      attempts: data['attempts'] as List<dynamic>? ?? [],
    );
  }

// 1. Update the getter for the main Result column
  String get formattedTime {
    if (bestTime >= 999999.0) {
      // If the team has finished all runs (DONE) or is explicitly marked as NP, show NP instead of N/A
      if (status == 'DONE' || status == 'NP') {
        return "NP";
      }
      return "N/A";
    }
    return bestTime.toStringAsFixed(3);
  }

// 2. Safely extract Left Target Time
  String getTimeLeft(int attemptIdx) {
    if (attemptIdx >= attempts.length) return "-";

    // Use 'is Map' instead of strict casting to avoid silent null failures
    var attemptData = attempts[attemptIdx];
    if (attemptData is! Map) return "-";

    var val = attemptData['time_left'];
    if (val is num) return val.toStringAsFixed(3);
    if (val == "NP") return "NP"; // Explicitly handle the "NP" string
    return val?.toString() ?? "-";
  }

// 3. Safely extract Right Target Time
  String getTimeRight(int attemptIdx) {
    if (attemptIdx >= attempts.length) return "-";

    var attemptData = attempts[attemptIdx];
    if (attemptData is! Map) return "-";

    var val = attemptData['time_right'];
    if (val is num) return val.toStringAsFixed(3);
    if (val == "NP") return "NP";
    return val?.toString() ?? "-";
  }

// 4. Safely extract Final Time
  String getRunFinalTime(int attemptIdx) {
    if (attemptIdx >= attempts.length) return "-";

    var attemptData = attempts[attemptIdx];
    if (attemptData is! Map) return "-";

    if (attemptData['state'] == 'NP') return "NP";

    var val = attemptData['final_time'];
    if (val == 999999 || val == 999999.0) return "NP";

    if (val is num) return val.toStringAsFixed(3);
    return val?.toString() ?? "-";
  }

  // Safely extract lane times for standard athletic tracks (Fallback)
  String getRunLaneTime(int attemptIdx, int laneIdx) {
    if (attemptIdx >= attempts.length) return "-";
    var attemptData = attempts[attemptIdx] as Map<String, dynamic>?;
    if (attemptData == null) return "-";

    // Fallback logic if needed for other sports
    String key = laneIdx == 0 ? 'time_left' : 'time_right';
    var val = attemptData[key];
    if (val is num) return val.toStringAsFixed(3);
    return val?.toString() ?? "-";
  }
}