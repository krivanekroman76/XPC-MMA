import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'theme_provider.dart';
import 'firebase_service.dart';
import 'home_screen.dart'; // Ensure this contains your RaceLeaderboard class
import 'settings_screen.dart';
import 'package:flutter/foundation.dart'; // REQUIRED for kIsWeb

class WelcomeScreen extends StatefulWidget {
  const WelcomeScreen({super.key});

  @override
  State<WelcomeScreen> createState() => _WelcomeScreenState();
}

class _WelcomeScreenState extends State<WelcomeScreen> {
  String? _savedLeague;
  bool _isLoading = true;

  // Subscription States
  Set<String> _subscribedRaces = {};
  bool _isGlobalSubscribed = false;

  @override
  void initState() {
    super.initState();
    _loadSavedData();
  }

  // Load saved league and notification preferences on startup
  Future<void> _loadSavedData() async {
    final prefs = await SharedPreferences.getInstance();
    final league = prefs.getString('saved_league');

    // Debugging line
    print("Loading Web Data: League: $league, Global: ${prefs.getBool('global_$league')}");

    setState(() {
      _subscribedRaces = (prefs.getStringList('subscribed_races') ?? []).toSet();
      if (league != null) {
        _isGlobalSubscribed = prefs.getBool('global_$league') ?? false;
      }
      _savedLeague = league;
      _isLoading = false;
    });
  }

  // Save a new league and reset global bell for that league context
  Future<void> _setLeague(String league) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('saved_league', league);

    setState(() {
      _savedLeague = league;
      _isGlobalSubscribed = prefs.getBool('global_$league') ?? false;
    });

    if (Scaffold.of(context).isDrawerOpen) {
      Navigator.pop(context);
    }
  }

  // Handle Global Bell Toggle
  Future<void> _toggleGlobalNotification() async {
    if (_savedLeague == null) return;

    // Ask for permission (Required for Web/iOS)
    NotificationSettings settings = await FirebaseMessaging.instance.requestPermission();

    if (settings.authorizationStatus == AuthorizationStatus.authorized) {
      bool newValue = !_isGlobalSubscribed;

      setState(() => _isGlobalSubscribed = newValue);

      // Let FirebaseService handle the platform differences (Topics vs Firestore Tokens)
      await FirebaseService().toggleMasterNotification(_savedLeague!, newValue);

      // Keep local UI state in sync
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool('global_$_savedLeague', newValue);
    }
  }

  // Handle Individual Race Bell Toggle
  Future<void> _toggleRaceNotification(String race) async {
    if (_savedLeague == null) return;

    NotificationSettings settings = await FirebaseMessaging.instance.requestPermission();

    if (settings.authorizationStatus == AuthorizationStatus.authorized) {
      bool isSubscribing = !_subscribedRaces.contains(race);

      setState(() {
        if (isSubscribing) {
          _subscribedRaces.add(race);
        } else {
          _subscribedRaces.remove(race);
        }
      });

      // Let FirebaseService handle the platform differences (Topics vs Firestore Tokens)
      await FirebaseService().setRaceNotification(_savedLeague!, race, isSubscribing);

      // Keep local UI state in sync
      final prefs = await SharedPreferences.getInstance();
      await prefs.setStringList('subscribed_races', _subscribedRaces.toList());
    }
  }

  @override
  Widget build(BuildContext context) {
    final tp = Provider.of<ThemeProvider>(context);
    final colorScheme = Theme.of(context).colorScheme;

    if (_isLoading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(
          _savedLeague == null
              ? tp.translateKey('league_selection')
              : '${tp.translateKey('races_label')} $_savedLeague',
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
        centerTitle: true,
        elevation: 0,
        actions: [
          // GLOBAL BELL: Only appears when a league is selected
          if (_savedLeague != null)
            IconButton(
              icon: Icon(
                _isGlobalSubscribed ? Icons.notifications_active : Icons.notifications_none,
                color: _isGlobalSubscribed ? Colors.amber : null,
              ),
              onPressed: _toggleGlobalNotification,
              tooltip: "League Notifications",
            ),
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const SettingsScreen()),
              );
            },
          ),
        ],
      ),
      drawer: _buildDrawer(tp, colorScheme),
      body: _savedLeague == null ? _buildLeagueSelection(tp) : _buildRaceSelection(tp, colorScheme),
    );
  }

  Widget _buildDrawer(ThemeProvider tp, ColorScheme colorScheme) {
    return Drawer(
      child: Column(
        children: [
          DrawerHeader(
            decoration: BoxDecoration(color: colorScheme.primary),
            child: Center(
              child: Text(tp.translateKey('change_league'),
                  style: const TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.bold)),
            ),
          ),
          Expanded(
            child: StreamBuilder<List<String>>(
              stream: FirebaseService().getLeaguesStream(),
              builder: (context, snapshot) {
                if (!snapshot.hasData) return const Center(child: CircularProgressIndicator());
                final leagues = snapshot.data!;
                return ListView.builder(
                  itemCount: leagues.length,
                  itemBuilder: (context, index) {
                    final league = leagues[index];
                    return ListTile(
                      leading: const Icon(Icons.emoji_events),
                      title: Text(league, style: const TextStyle(fontWeight: FontWeight.bold)),
                      selected: _savedLeague == league,
                      selectedColor: colorScheme.primary,
                      onTap: () => _setLeague(league),
                    );
                  },
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLeagueSelection(ThemeProvider tp) {
    return StreamBuilder<List<String>>(
      stream: FirebaseService().getLeaguesStream(),
      builder: (context, snapshot) {
        if (snapshot.hasError) return Center(child: Text("Error: ${snapshot.error}"));
        if (!snapshot.hasData) return const Center(child: CircularProgressIndicator());

        final leagues = snapshot.data!;
        return ListView.builder(
          padding: const EdgeInsets.all(16),
          itemCount: leagues.length,
          itemBuilder: (context, index) {
            return Card(
              elevation: 4,
              margin: const EdgeInsets.symmetric(vertical: 8),
              child: ListTile(
                contentPadding: const EdgeInsets.all(16),
                leading: const Icon(Icons.emoji_events, size: 40, color: Colors.amber),
                title: Text(leagues[index], style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                trailing: const Icon(Icons.arrow_forward_ios),
                onTap: () => _setLeague(leagues[index]),
              ),
            );
          },
        );
      },
    );
  }

  Widget _buildRaceSelection(ThemeProvider tp, ColorScheme colorScheme) {
    return StreamBuilder<List<String>>(
      stream: FirebaseService().getRacesStream(_savedLeague!),
      builder: (context, snapshot) {
        if (snapshot.hasError) return Center(child: Text("Error: ${snapshot.error}"));
        if (!snapshot.hasData) return const Center(child: CircularProgressIndicator());

        final races = snapshot.data!;
        if (races.isEmpty) {
          return Center(child: Text(tp.translateKey('no_races'), style: const TextStyle(fontSize: 18)));
        }

        return ListView.builder(
          padding: const EdgeInsets.all(16),
          itemCount: races.length,
          itemBuilder: (context, index) {
            final race = races[index];
            bool isRaceSubscribed = _subscribedRaces.contains(race);

            return Card(
              elevation: 2,
              margin: const EdgeInsets.symmetric(vertical: 8),
              child: ListTile(
                contentPadding: const EdgeInsets.only(left: 16, right: 8),
                leading: Icon(Icons.flag, size: 30, color: colorScheme.primary),
                title: Text(race, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    // INDIVIDUAL RACE BELL
                    IconButton(
                      icon: Icon(
                        (_isGlobalSubscribed || isRaceSubscribed)
                            ? Icons.notifications_active
                            : Icons.notifications_none,
                        color: (_isGlobalSubscribed || isRaceSubscribed) ? colorScheme.primary : Colors.grey,
                      ),
                      onPressed: () => _toggleRaceNotification(race),
                    ),
                    const Icon(Icons.play_arrow),
                  ],
                ),
                onTap: () async {
                  final prefs = await SharedPreferences.getInstance();
                  await prefs.setString('active_race', race);

                  if (mounted) {
                    Navigator.pushReplacement(
                      context,
                      MaterialPageRoute(
                        builder: (context) => RaceLeaderboard(
                            initialLeague: _savedLeague!,
                            initialRace: race
                        ),
                      ),
                    );
                  }
                },
              ),
            );
          },
        );
      },
    );
  }
}