import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';

class ThemeProvider extends ChangeNotifier {
  bool _isDarkMode = true;
  Locale _locale = const Locale('en');
  Color _seedColor = Colors.blue;
  final SharedPreferences _prefs;

  final List<Color> availableColors = [
    Colors.blue,
    Colors.red,
    Colors.green,
    Colors.orange,
    Colors.deepPurple,
    Colors.yellow.shade700,
  ];

  // This is no longer final! It starts with defaults but can be expanded by OTA downloads.
  Map<String, Map<String, String>> _dictionary = {
    'en': {
      'invalid_attempt': 'Invalid attempt',
      'time_improved': 'Time improved!',
      'time_worse': 'Slower time',
      'reason_nozzle': 'Disconnected nozzle',
      'reason_line': 'Line fault',
      'settings_title': 'Settings',
      'appearance': 'Appearance',
      'dark_mode': 'Dark Mode',
      'app_color': 'App Color',
      'languages_downloads': 'Languages (Downloads)',
      'downloading': 'Downloading',
      'download_complete': 'Download complete!',
      'download_failed': 'Failed to download.',
      'update_available': 'Update available',
      'ready_to_use': 'Ready to use',
      'not_downloaded': 'Not downloaded',
      'download_first': 'Please download the language first.',
      'language': 'Language',
      // NEW KEYS FOR WELCOME & HOME SCREENS
      'league_selection': 'League Selection',
      'races_label': 'Races:',
      'change_league': 'Change League',
      'no_races': 'No races in this league.',
      'all': 'All',
      'men': 'Men',
      'women': 'Women',
      'youth': 'Youth',
      'subscribed_all': 'You are already subscribed to all.',
      'app_title': 'Stopwatch\nLeaderboard',
      'main_menu': 'Main Menu',
      'st': 'ST',
      'team': 'TEAM',
      'result': 'RESULT',
    },
  };

  ThemeProvider(this._prefs) {
    _isDarkMode = _prefs.getBool('isDarkMode') ?? true;
    String lang = _prefs.getString('language') ?? 'en';
    _locale = Locale(lang);

    int colorValue = _prefs.getInt('seedColor') ?? Colors.blue.value;
    _seedColor = Color(colorValue);

    // Load any downloaded languages from local storage on startup
    _loadSavedTranslations();
  }

  bool get isDarkMode => _isDarkMode;
  Locale get locale => _locale;
  Color get seedColor => _seedColor;

  void toggleTheme() {
    _isDarkMode = !_isDarkMode;
    _prefs.setBool('isDarkMode', _isDarkMode);
    notifyListeners();
  }

  void setColor(Color color) {
    _seedColor = color;
    _prefs.setInt('seedColor', color.value);
    notifyListeners();
  }

  // --- NEW: Set language explicitly (better for dropdowns/lists in settings) ---
  void setLanguage(String langCode) {
    _locale = Locale(langCode);
    _prefs.setString('language', langCode);
    notifyListeners();
  }

  // --- OTA TRANSLATIONS LOGIC ---

  // Reads SharedPreferences to see if we downloaded new dictionaries
  void _loadSavedTranslations() {
    String? versionsStr = _prefs.getString('local_lang_versions');
    if (versionsStr != null) {
      try {
        Map<String, dynamic> versions = json.decode(versionsStr);

        for (String langCode in versions.keys) {
          String? langJson = _prefs.getString('lang_$langCode');
          if (langJson != null) {
            Map<String, dynamic> decoded = json.decode(langJson);
            // Convert dynamic map back to Map<String, String>
            Map<String, String> typedMap = decoded.map((key, value) => MapEntry(key, value.toString()));

            // Overwrite or add the language to our live dictionary
            _dictionary[langCode] = typedMap;
          }
        }
      } catch (e) {
        debugPrint("Error loading saved translations: $e");
      }
    }
  }

  // Call this from LanguageSettingsScreen immediately after a successful download!
  void reloadTranslations() {
    _loadSavedTranslations();
    notifyListeners(); // Tells the whole app to rebuild with the new words
  }

  // --- TRANSLATION ---

  String translateKey(String key) {
    return _dictionary[_locale.languageCode]?[key] ?? key;
  }
}