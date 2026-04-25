import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';
import 'theme_provider.dart';
import 'firebase_service.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  Map<String, dynamic> _onlineVersions = {};
  Map<String, int> _localVersions = {};
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadLanguageData();
  }

  Future<void> _loadLanguageData() async {
    setState(() => _isLoading = true);

    // 1. Get local versions saved on the device
    final prefs = await SharedPreferences.getInstance();
    final localVersionsStr = prefs.getString('local_lang_versions') ?? '{}';
    _localVersions = Map<String, int>.from(json.decode(localVersionsStr));

    // 2. Get online versions from Firestore
    _onlineVersions = await FirebaseService().getTranslationVersions();

    setState(() => _isLoading = false);
  }

  Future<void> _downloadLanguage(String langCode, int onlineVersion, ThemeProvider tp) async {
    ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('${tp.translateKey('downloading')} $langCode...'))
    );

    final langData = await FirebaseService().downloadLanguageData(langCode);

    if (langData.isNotEmpty) {
      final prefs = await SharedPreferences.getInstance();

      // Save dictionary locally
      await prefs.setString('lang_$langCode', json.encode(langData));

      // Update local version tracker
      _localVersions[langCode] = onlineVersion;
      await prefs.setString('local_lang_versions', json.encode(_localVersions));

      if (mounted) {
        // Tell the app to reload dictionaries
        Provider.of<ThemeProvider>(context, listen: false).reloadTranslations();
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(tp.translateKey('download_complete')), backgroundColor: Colors.green)
        );
        setState(() {});
      }
    } else {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(tp.translateKey('download_failed')), backgroundColor: Colors.red)
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final tp = Provider.of<ThemeProvider>(context);

    return Scaffold(
      appBar: AppBar(
        title: Text(tp.translateKey('settings_title')),
        elevation: 0,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
        padding: const EdgeInsets.all(16.0),
        children: [
          // --- APPEARANCE SECTION ---
          Text(tp.translateKey('appearance'), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          const SizedBox(height: 10),

          // Dark Mode Toggle
          SwitchListTile(
            title: Text(tp.translateKey('dark_mode')),
            secondary: Icon(tp.isDarkMode ? Icons.dark_mode : Icons.light_mode),
            value: tp.isDarkMode,
            onChanged: (value) => tp.toggleTheme(),
          ),

          const SizedBox(height: 10),
          Text(tp.translateKey('app_color'), style: const TextStyle(fontSize: 14, color: Colors.grey)),
          const SizedBox(height: 10),

          // Color Palette (Horizontal Chips)
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: tp.availableColors.map((color) => GestureDetector(
                onTap: () => tp.setColor(color),
                child: Container(
                  margin: const EdgeInsets.only(right: 12),
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: color,
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: tp.seedColor == color ? (tp.isDarkMode ? Colors.white : Colors.black) : Colors.transparent,
                      width: 3,
                    ),
                  ),
                ),
              )).toList(),
            ),
          ),

          const Padding(padding: EdgeInsets.symmetric(vertical: 20.0), child: Divider()),

          // --- LANGUAGE & DOWNLOADS SECTION ---
          Text(tp.translateKey('languages_downloads'), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          const SizedBox(height: 10),

          ..._onlineVersions.keys.map((langCode) {
            int onlineVersion = _onlineVersions[langCode] is int
                ? _onlineVersions[langCode]
                : int.tryParse(_onlineVersions[langCode].toString()) ?? 1;

            int localVersion = _localVersions[langCode] ?? 0;
            bool isBuiltIn = langCode == 'cs' || langCode == 'en';

            // If it's built-in, we assume we start at version 1 (the hardcoded dictionary).
            int effectiveLocalVersion = localVersion > 0 ? localVersion : (isBuiltIn ? 1 : 0);

            bool isDownloaded = localVersion > 0;

            // Now, updates work for EVERYTHING! If Firestore is v2, and we have v1, update = true!
            bool updateAvailable = onlineVersion > effectiveLocalVersion;
            bool isCurrentlySelected = tp.locale.languageCode == langCode;

            // Smart Subtitle Logic
            String subtitleText;
            if (updateAvailable) {
              subtitleText = '${tp.translateKey('update_available')} (v$onlineVersion)';
            } else if (isDownloaded) {
              subtitleText = tp.translateKey('ready_to_use');
            } else if (isBuiltIn) {
              subtitleText = 'Default (Built-in)'; // Fixes the "not downloaded" text!
            } else {
              subtitleText = tp.translateKey('not_downloaded');
            }

            return Card(
              elevation: isCurrentlySelected ? 2 : 0,
              color: isCurrentlySelected ? Theme.of(context).colorScheme.primary.withOpacity(0.1) : null,
              child: ListTile(
                leading: CircleAvatar(
                  backgroundColor: isCurrentlySelected ? Theme.of(context).colorScheme.primary : Colors.grey,
                  child: Text(langCode.toUpperCase(), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                ),
                title: Text('${tp.translateKey('language')}: ${langCode.toUpperCase()}', style: TextStyle(fontWeight: isCurrentlySelected ? FontWeight.bold : FontWeight.normal)),
                subtitle: Text(subtitleText),
                // Notice we now pass `isBuiltIn` to the helper function
                trailing: _buildTrailingAction(langCode, onlineVersion, isDownloaded, isBuiltIn, updateAvailable, isCurrentlySelected, tp),
                onTap: () {
                  if (isDownloaded || isBuiltIn) {
                    tp.setLanguage(langCode);
                  } else {
                    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tp.translateKey('download_first'))));
                  }
                },
              ),
            );
          }),
        ],
      ),
    );
  }

  Widget _buildTrailingAction(String langCode, int onlineVersion, bool isDownloaded, bool isBuiltIn, bool updateAvailable, bool isCurrentlySelected, ThemeProvider tp) {
    if (updateAvailable) {
      // 1. If an update exists on Firestore, show the orange update button for ANY language.
      return IconButton(
        icon: const Icon(Icons.system_update, color: Colors.orange),
        onPressed: () => _downloadLanguage(langCode, onlineVersion, tp),
      );
    } else if (!isDownloaded && !isBuiltIn) {
      // 2. If it's a completely new language (like 'fr') that isn't downloaded, show cloud icon.
      return IconButton(
        icon: const Icon(Icons.cloud_download),
        onPressed: () => _downloadLanguage(langCode, onlineVersion, tp),
      );
    } else if (isCurrentlySelected) {
      // 3. If it's up to date and selected, show the green check.
      return const Icon(Icons.check_circle, color: Colors.green);
    } else {
      // 4. If it's up to date but not selected, show nothing.
      return const SizedBox.shrink();
    }
  }
}