import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'firebase_service.dart';
import 'team_model.dart';
import 'home_screen.dart';
import 'theme_provider.dart';

class WelcomeScreen extends StatefulWidget {
  const WelcomeScreen({super.key});

  @override
  State<WelcomeScreen> createState() => _WelcomeScreenState();
}

class _WelcomeScreenState extends State<WelcomeScreen> {
  bool _masterNotifications = false;

  @override
  void initState() {
    super.initState();
    _loadMasterNotificationState();
  }

  void _loadMasterNotificationState() {
    setState(() {
      _masterNotifications = FirebaseService().isMasterNotificationEnabled;
    });
  }

  @override
  Widget build(BuildContext context) {
    final themeProvider = Provider.of<ThemeProvider>(context);
    final colorScheme = Theme.of(context).colorScheme; // Získáme aktuální barvy

    return Scaffold(
      appBar: AppBar(
        title: Text(themeProvider.translate('XPC-MMA Závody', 'XPC-MMA Races')),
        elevation: 0,
        actions: [
          // Výběr barvy
          PopupMenuButton<Color>(
            icon: Icon(Icons.palette, color: colorScheme.primary),
            onSelected: (color) => themeProvider.setColor(color),
            itemBuilder: (context) => themeProvider.availableColors.map((color) => PopupMenuItem(
              value: color,
              child: Container(
                width: 24, height: 24,
                decoration: BoxDecoration(color: color, shape: BoxShape.circle),
              ),
            )).toList(),
          ),
          TextButton(
            onPressed: () => themeProvider.toggleLanguage(),
            child: Text(
              themeProvider.locale.languageCode.toUpperCase(),
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: colorScheme.primary),
            ),
          ),
          IconButton(
            icon: Icon(themeProvider.isDarkMode ? Icons.light_mode : Icons.dark_mode),
            onPressed: () => themeProvider.toggleTheme(),
          ),
        ],
      ),
      body: Column(
        children: [
          Container(
            color: colorScheme.primary.withOpacity(0.1),
            child: SwitchListTile(
              title: Text(themeProvider.translate('Odebírat všechny závody', 'Subscribe to all races'), style: const TextStyle(fontWeight: FontWeight.bold)),
              subtitle: Text(themeProvider.translate('Dostávat upozornění na každý výsledek.', 'Get notified for every result.')),
              value: _masterNotifications,
              activeColor: colorScheme.primary,
              onChanged: (bool value) async {
                if (value) {
                  bool success = await FirebaseService().init();
                  if (!success) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text(themeProvider.translate('Chyba: Prohlížeč zablokoval spojení.', 'Error: Connection blocked by browser.')),
                        backgroundColor: Colors.red,
                        duration: const Duration(seconds: 4),
                      ),
                    );
                    return;
                  }
                }
                await FirebaseService().setMasterNotification(value);
                setState(() {
                  _masterNotifications = value;
                });
              },
            ),
          ),
          const Divider(height: 1),
          Expanded(
            child: StreamBuilder<List<String>>(
              stream: FirebaseService().getRacesStream(),
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (snapshot.hasError) return Center(child: Text('Error: ${snapshot.error}'));

                final races = snapshot.data ?? [];
                if (races.isEmpty) {
                  return Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.flag_outlined, size: 80, color: Colors.grey.shade400),
                        const SizedBox(height: 16),
                        Text(
                            themeProvider.translate('Momentálně nejsou vypsány\nžádné závody.', 'Currently there are no\nraces available.'),
                            textAlign: TextAlign.center,
                            style: const TextStyle(fontSize: 18, color: Colors.grey)
                        ),
                      ],
                    ),
                  );
                }

                return ListView.builder(
                  padding: const EdgeInsets.all(12),
                  itemCount: races.length,
                  itemBuilder: (context, index) {
                    final raceName = races[index];
                    bool isSubscribed = FirebaseService().isRaceNotificationEnabled(raceName);

                    return StreamBuilder<RaceSettings>(
                        stream: FirebaseService().getSettingsStream(raceName),
                        builder: (context, settingsSnapshot) {
                          bool isFinished = settingsSnapshot.data?.isFinished ?? false;

                          return Card(
                            elevation: 2,
                            margin: const EdgeInsets.symmetric(vertical: 8),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                            child: ListTile(
                              contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
                              leading: CircleAvatar(
                                backgroundColor: isFinished ? Colors.grey : colorScheme.primary,
                                child: Icon(isFinished ? Icons.flag : Icons.directions_run, color: Colors.white),
                              ),
                              title: Text(raceName, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                              subtitle: Text(isFinished
                                  ? themeProvider.translate('Závod byl ukončen', 'Race is finished')
                                  : themeProvider.translate('Klikněte pro výsledky', 'Click for results')),
                              trailing: isFinished
                                  ? const SizedBox()
                                  : _masterNotifications
                                  ? IconButton(
                                icon: Icon(Icons.notifications_active, color: colorScheme.primary),
                                onPressed: () {
                                  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(themeProvider.translate('Už odebíráte všechny závody.', 'You are already subscribed to all.'))));
                                },
                              )
                                  : Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  IconButton(
                                    icon: Icon(
                                      isSubscribed ? Icons.notifications_active : Icons.notifications_none,
                                      color: isSubscribed ? colorScheme.primary : Colors.grey,
                                    ),
                                    onPressed: () async {
                                      if (!isSubscribed) {
                                        bool success = await FirebaseService().init();
                                        if (!success) return;
                                      }
                                      await FirebaseService().setRaceNotification(raceName, !isSubscribed);
                                      setState(() {});
                                      ScaffoldMessenger.of(context).showSnackBar(
                                          SnackBar(
                                              content: Text(!isSubscribed ? themeProvider.translate('Odběr zapnut', 'Subscribed') : themeProvider.translate('Odběr vypnut', 'Unsubscribed')),
                                              backgroundColor: !isSubscribed ? Colors.green : Colors.grey,
                                              duration: const Duration(seconds: 2)
                                          )
                                      );
                                    },
                                  ),
                                  const Icon(Icons.arrow_forward_ios, size: 16, color: Colors.grey),
                                ],
                              ),
                              onTap: () {
                                Navigator.push(context, MaterialPageRoute(builder: (context) => RaceLeaderboard(initialRace: raceName)));
                              },
                            ),
                          );
                        }
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
}