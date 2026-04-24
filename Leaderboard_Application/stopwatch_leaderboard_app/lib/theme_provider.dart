import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ThemeProvider extends ChangeNotifier {
  bool _isDarkMode = true;
  Locale _locale = const Locale('cs');
  Color _seedColor = Colors.blue; // Výchozí modrý vibe
  final SharedPreferences _prefs;

  // Seznam barev pro výběr
  final List<Color> availableColors = [
    Colors.blue,
    Colors.red,
    Colors.green,
    Colors.orange,
    Colors.deepPurple,
    Colors.yellow.shade700,
  ];

  ThemeProvider(this._prefs) {
    _isDarkMode = _prefs.getBool('isDarkMode') ?? true;
    String lang = _prefs.getString('language') ?? 'cs';
    _locale = Locale(lang);

    // Načtení uložené barvy (pokud není, dá modrou)
    int colorValue = _prefs.getInt('seedColor') ?? Colors.blue.value;
    _seedColor = Color(colorValue);
  }

  bool get isDarkMode => _isDarkMode;
  Locale get locale => _locale;
  Color get seedColor => _seedColor;

  void toggleTheme() {
    _isDarkMode = !_isDarkMode;
    _prefs.setBool('isDarkMode', _isDarkMode);
    notifyListeners();
  }

  void toggleLanguage() {
    _locale = _locale.languageCode == 'cs' ? const Locale('en') : const Locale('cs');
    _prefs.setString('language', _locale.languageCode);
    notifyListeners();
  }

  void setColor(Color color) {
    _seedColor = color;
    _prefs.setInt('seedColor', color.value);
    notifyListeners();
  }

  String translate(String cs, String en) {
    return _locale.languageCode == 'cs' ? cs : en;
  }
}