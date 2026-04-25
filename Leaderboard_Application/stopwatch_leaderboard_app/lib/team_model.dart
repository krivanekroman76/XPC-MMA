class RaceSettings {
  final int attemptsCount;
  final int lanesCount;
  final int sectionsCount; // ADDED: To determine if we need L and R columns
  final String logic;      // ADDED: e.g., "attack" vs "standard"
  final bool isFinished;

  RaceSettings({
    required this.attemptsCount,
    required this.lanesCount,
    required this.sectionsCount,
    required this.logic,
    required this.isFinished,
  });

  factory RaceSettings.fromMap(Map<String, dynamic>? data) {
    if (data == null) return RaceSettings.defaultSettings();
    return RaceSettings(
      attemptsCount: data['attempts'] ?? 2,
      lanesCount: data['lanes'] ?? 1,
      sectionsCount: data['sections'] ?? 1, // Default to 1 if missing
      logic: data['logic'] ?? 'standard',
      isFinished: false, // Update this if you have a finished flag in your DB
    );
  }

  static RaceSettings defaultSettings() => RaceSettings(
    attemptsCount: 2,
    lanesCount: 1,
    sectionsCount: 1,
    logic: 'standard',
    isFinished: false,
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

  String get formattedTime {
    if (bestTime >= 999999.0) return "N/A";
    return bestTime.toStringAsFixed(3);
  }

  // --- NEW: Safely extract Left Target Time ---
  String getTimeLeft(int attemptIdx) {
    if (attemptIdx >= attempts.length) return "-";
    var attemptData = attempts[attemptIdx] as Map<String, dynamic>?;
    if (attemptData == null) return "-";

    var val = attemptData['time_left'];
    if (val is num) return val.toStringAsFixed(3);
    return val?.toString() ?? "-"; // Returns "--.---" if it's a string
  }

  // --- NEW: Safely extract Right Target Time ---
  String getTimeRight(int attemptIdx) {
    if (attemptIdx >= attempts.length) return "-";
    var attemptData = attempts[attemptIdx] as Map<String, dynamic>?;
    if (attemptData == null) return "-";

    var val = attemptData['time_right'];
    if (val is num) return val.toStringAsFixed(3);
    return val?.toString() ?? "-"; // Returns "--.---" if it's a string
  }

  // --- UPDATED: Safely extract Final Time (handles both string and num) ---
  String getRunFinalTime(int attemptIdx) {
    if (attemptIdx >= attempts.length) return "-";
    var attemptData = attempts[attemptIdx] as Map<String, dynamic>?;
    if (attemptData == null) return "-";

    // If NP return NP not 99999 time
    if (attemptData['state'] == 'NP') {
      return "NP";
    }

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