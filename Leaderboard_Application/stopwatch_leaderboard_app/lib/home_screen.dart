import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'firebase_service.dart';
import 'team_model.dart';
import 'welcome_screen.dart';
import 'dart:async';
import 'theme_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'settings_screen.dart';

enum SortType { rank, startNo }

class RaceLeaderboard extends StatefulWidget {
  final String initialLeague;
  final String initialRace;

  const RaceLeaderboard({
    super.key,
    required this.initialLeague,
    required this.initialRace,
  });

  @override
  State<RaceLeaderboard> createState() => _RaceLeaderboardState();
}

class _RaceLeaderboardState extends State<RaceLeaderboard> {
  late String selectedLeague;
  late String selectedRace;
  String selectedCategory = "Vše";
  SortType currentSort = SortType.rank;

  Map<String, double> previousBestTimes = {};

  @override
  void initState() {
    super.initState();
    selectedLeague = widget.initialLeague;
    selectedRace = widget.initialRace;
  }

  String getTranslatedCategory(String cat, ThemeProvider tp) {
    if (cat == "Vše") return tp.translateKey("all");
    if (cat == "Muži") return tp.translateKey("men");
    if (cat == "Ženy") return tp.translateKey("women");
    if (cat == "Dorost") return tp.translateKey("youth");
    return cat;
  }

  @override
  Widget build(BuildContext context) {
    String uniqueRaceId = "${selectedLeague}_$selectedRace";

    final themeProvider = Provider.of<ThemeProvider>(context);
    final colorScheme = Theme.of(context).colorScheme;

    return OrientationBuilder(
      builder: (context, orientation) {
        final bool isLandscape = orientation == Orientation.landscape;

        return Scaffold(
          appBar: AppBar(
            leading: IconButton(
              icon: const Icon(Icons.arrow_back),
              onPressed: () async {
                final prefs = await SharedPreferences.getInstance();
                await prefs.remove('active_race');
                if (mounted) {
                  Navigator.pushReplacement(
                    context,
                    MaterialPageRoute(builder: (context) => const WelcomeScreen()),
                  );
                }
              },
            ),
            title: Text(selectedRace, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
            elevation: 0,
            actions: [
              IconButton(
                icon: const Icon(Icons.settings),
                onPressed: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (context) => const SettingsScreen()),
                  );
                },
              ),
              StreamBuilder<RaceSettings>(
                  stream: FirebaseService().getSettingsStream(selectedLeague, selectedRace),
                  builder: (context, snapshot) {
                    // Use the logic from your FirebaseService/Prefs
                    bool isGlobalOn = FirebaseService().isMasterOn;
                    bool isSubscribed = FirebaseService().isRaceNotificationEnabled(selectedRace);

                    return IconButton(
                      icon: Icon(
                        (isGlobalOn || isSubscribed) ? Icons.notifications_active : Icons.notifications_none,
                        color: (isGlobalOn || isSubscribed) ? colorScheme.primary : Colors.grey,
                      ),
                      onPressed: isGlobalOn
                          ? () {
                        _showToast(context, themeProvider.translateKey('global_is_active'), colorScheme.secondary, Icons.info);
                      }
                          : () async {
                        // Call the specific toggle method you defined
                        // Ensure this method is accessible (Static or via instance)
                        await FirebaseService().setRaceNotification(selectedLeague, selectedRace, !isSubscribed);

                        setState(() {}); // Refresh the bell icon color

                        _showToast(
                            context,
                            !isSubscribed ? themeProvider.translateKey('notif_on') : themeProvider.translateKey('notif_off'),
                            !isSubscribed ? Colors.green : Colors.grey,
                            !isSubscribed ? Icons.notifications_active : Icons.notifications_off
                        );
                      },
                    );
                  }
              ),
              IconButton(
                icon: Icon(currentSort == SortType.rank ? Icons.emoji_events : Icons.list),
                onPressed: () => setState(() => currentSort = currentSort == SortType.rank ? SortType.startNo : SortType.rank),
              ),
            ],
          ),
          drawer: _buildDrawer(themeProvider, colorScheme),
          body: StreamBuilder<RaceSettings>(
              stream: FirebaseService().getSettingsStream(selectedLeague, selectedRace),
              builder: (context, settingsSnapshot) {
                final settings = settingsSnapshot.data ?? RaceSettings.defaultSettings();
                return Column(
                  children: [
                    _buildCategoryFilter(themeProvider, colorScheme),
                    _buildHeader(isLandscape, settings, themeProvider),
                    Expanded(
                      child: _buildTeamList(isLandscape, settings, themeProvider),
                    ),
                  ],
                );
              }
          ),
        );
      },
    );
  }

  Widget _buildDrawer(ThemeProvider tp, ColorScheme colorScheme) {
    return Drawer(
      child: Column(
        children: [
          DrawerHeader(
            decoration: BoxDecoration(color: colorScheme.primary),
            child: Center(
              child: Text(tp.translateKey('xpc_races'), style: const TextStyle(color: Colors.white, fontSize: 24), textAlign: TextAlign.center),
            ),
          ),
          ListTile(
            leading: const Icon(Icons.home),
            title: Text(tp.translateKey('main_menu')),
            onTap: () {
              Navigator.of(context).pushAndRemoveUntil(
                MaterialPageRoute(builder: (context) => const WelcomeScreen()),
                    (route) => false,
              );
            },
          ),
          const Divider(),
          Expanded(
            child: StreamBuilder<List<String>>(
              stream: FirebaseService().getRacesStream(selectedLeague),
              builder: (context, snapshot) {
                final races = snapshot.data ?? [];
                return ListView.builder(
                  itemCount: races.length,
                  itemBuilder: (context, index) {
                    final raceName = races[index];
                    return ListTile(
                      leading: const Icon(Icons.flag_rounded),
                      title: Text(raceName),
                      selected: selectedRace == raceName,
                      selectedColor: colorScheme.primary,
                      onTap: () {
                        if (selectedRace != raceName) setState(() => selectedRace = raceName);
                        Navigator.pop(context);
                      },
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

  Widget _buildCategoryFilter(ThemeProvider tp, ColorScheme colorScheme) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: ["Vše", "Muži", "Ženy", "Dorost"].map((cat) => Padding(
            padding: const EdgeInsets.symmetric(horizontal: 5.0),
            child: ChoiceChip(
              label: Text(getTranslatedCategory(cat, tp)),
              selected: selectedCategory == cat,
              onSelected: (s) {
                if (s) setState(() => selectedCategory = cat);
              },
              selectedColor: colorScheme.primary,
              labelStyle: TextStyle(color: selectedCategory == cat ? Colors.white : (tp.isDarkMode ? Colors.white70 : Colors.black87), fontSize: 13),
              backgroundColor: tp.isDarkMode ? Colors.grey[900] : Colors.grey[300],
            ),
          )).toList(),
        ),
      ),
    );
  }

  Widget _buildHeader(bool isLandscape, RaceSettings settings, ThemeProvider tp) {
    Color bgColor = tp.isDarkMode ? Colors.black : Colors.grey.shade300;
    Color textColor = tp.isDarkMode ? Colors.grey : Colors.black87;

    return Container(
      padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 8),
      color: bgColor,
      child: Row(
        children: [
          SizedBox(width: 40, child: Text(tp.translateKey('st'), style: TextStyle(color: textColor, fontWeight: FontWeight.bold, fontSize: 10))),
          SizedBox(width: 25, child: Text('#', style: TextStyle(color: textColor, fontWeight: FontWeight.bold, fontSize: 10))),
          if (isLandscape) ...[
            SizedBox(width: 30, child: Text('Pos', style: TextStyle(color: textColor, fontWeight: FontWeight.bold, fontSize: 10), textAlign: TextAlign.center)),
            SizedBox(width: 30, child: Text('Cat', style: TextStyle(color: textColor, fontWeight: FontWeight.bold, fontSize: 10), textAlign: TextAlign.center)),
          ],
          Expanded(child: Text(tp.translateKey('team'), style: TextStyle(color: textColor, fontWeight: FontWeight.bold, fontSize: 10))),
          SizedBox(width: 75, child: Text(tp.translateKey('result'), style: TextStyle(color: textColor, fontWeight: FontWeight.bold, fontSize: 10), textAlign: TextAlign.center)),
          if (isLandscape) ..._buildHeaderLanes(settings, textColor),
        ],
      ),
    );
  }

  List<Widget> _buildHeaderLanes(RaceSettings settings, Color textColor) {
    List<Widget> widgets = [];
    for (int i = 0; i < settings.attemptsCount; i++) {
      if (settings.sectionsCount == 2) {
        widgets.add(SizedBox(width: 42, child: Text('L${i + 1}', style: TextStyle(color: textColor, fontSize: 10, fontWeight: FontWeight.bold), textAlign: TextAlign.center)));
        widgets.add(SizedBox(width: 42, child: Text('R${i + 1}', style: TextStyle(color: textColor, fontSize: 10, fontWeight: FontWeight.bold), textAlign: TextAlign.center)));
      } else {
        for (int j = 0; j < settings.lanesCount; j++) {
          widgets.add(SizedBox(width: 42, child: Text('L${j + 1}', style: TextStyle(color: textColor, fontSize: 8), textAlign: TextAlign.center)));
        }
      }
      widgets.add(SizedBox(width: 45, child: Text('B${i + 1}', style: TextStyle(color: textColor, fontSize: 10, fontWeight: FontWeight.bold), textAlign: TextAlign.center)));
    }
    return widgets;
  }

  List<Widget> _buildRowLanes(Team team, RaceSettings settings, Color textColor) {
    List<Widget> widgets = [];
    for (int i = 0; i < settings.attemptsCount; i++) {
      if (settings.sectionsCount == 2) {
        widgets.add(SizedBox(width: 42, child: Text(team.getTimeLeft(i), style: TextStyle(color: textColor.withOpacity(0.7), fontSize: 11), textAlign: TextAlign.center)));
        widgets.add(SizedBox(width: 42, child: Text(team.getTimeRight(i), style: TextStyle(color: textColor.withOpacity(0.7), fontSize: 11), textAlign: TextAlign.center)));
      } else {
        for (int j = 0; j < settings.lanesCount; j++) {
          widgets.add(SizedBox(width: 42, child: Text(team.getRunLaneTime(i, j), style: TextStyle(color: textColor.withOpacity(0.7), fontSize: 11), textAlign: TextAlign.center)));
        }
      }
      widgets.add(SizedBox(width: 45, child: Text(team.getRunFinalTime(i), style: TextStyle(color: textColor.withOpacity(0.7), fontSize: 11, fontWeight: FontWeight.bold), textAlign: TextAlign.center)));
    }
    return widgets;
  }

  Widget _buildTeamList(bool isLandscape, RaceSettings settings, ThemeProvider tp) {
    return StreamBuilder<List<Team>>(
      key: ValueKey('$selectedLeague-$selectedRace-$selectedCategory'),
      stream: FirebaseService().getTeamsStream(selectedLeague, selectedRace, selectedCategory),
      builder: (context, snapshot) {
        if (!snapshot.hasData) return const Center(child: CircularProgressIndicator());
        var teams = snapshot.data!;

        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (!mounted) return;

          for (var team in teams) {
            if (!previousBestTimes.containsKey(team.id)) {
              previousBestTimes[team.id] = team.bestTime;
              continue;
            }

            double oldTime = previousBestTimes[team.id]!;
            double newTime = team.bestTime;

            if (oldTime != newTime && newTime > 0) {
              if (newTime == 999999.0 && oldTime != 999999.0) {
                _showToast(context, "${team.name}: ${tp.translateKey('invalid_attempt')}", Colors.red, Icons.cancel);
              } else if (newTime < oldTime || oldTime >= 999999.0) {
                _showToast(context, "${team.name}: ${tp.translateKey('time_improved')} (${newTime.toStringAsFixed(3)})", Colors.green, Icons.trending_up);
              } else if (newTime > oldTime && oldTime > 0) {
                _showToast(context, "${team.name}: ${tp.translateKey('time_worse')}", Colors.orange, Icons.trending_down);
              }
              previousBestTimes[team.id] = newTime;
            }
          }
        });

        final fullSortedList = List<Team>.from(teams);
        fullSortedList.sort((a, b) {
          bool aHasTime = a.bestTime > 0 && a.bestTime < 999999;
          bool bHasTime = b.bestTime > 0 && b.bestTime < 999999;
          if (aHasTime && bHasTime) return a.bestTime.compareTo(b.bestTime);
          if (aHasTime) return -1;
          if (bHasTime) return 1;
          return a.startNo.compareTo(b.startNo);
        });

        final Map<String, Map<String, int>> ranks = {};
        for (var cat in ["Muži", "Ženy", "Dorost"]) {
          var catTeams = fullSortedList.where((t) => t.category == cat).toList();
          ranks[cat] = { for (var i = 0; i < catTeams.length; i++) catTeams[i].id: i + 1};
        }

        if (currentSort == SortType.startNo) {
          // 1. Extract the base sequence of categories from Firestore run_order
          // E.g., translates ["Muži - 1. Pokus", "Ženy - 1. Pokus"] into ["Muži", "Ženy"]
          List<String> baseCategorySequence = [];
          for (String block in settings.runOrder) {
            String cat = block.split(' - ').first.trim();
            if (!baseCategorySequence.contains(cat)) {
              baseCategorySequence.add(cat);
            }
          }

          // Fallback just in case run_order is completely empty in Firestore
          if (baseCategorySequence.isEmpty) {
            baseCategorySequence = ["Muži", "Ženy", "Dorost"];
          }

          // 2. Sort the teams chronologically
          teams.sort((a, b) {
            // First, find where each team's category sits in the overall event timeline
            int catAIndex = baseCategorySequence.indexOf(a.category);
            int catBIndex = baseCategorySequence.indexOf(b.category);

            // Safety check: if a category isn't in the run_order, push it to the bottom
            if (catAIndex == -1) catAIndex = 999;
            if (catBIndex == -1) catBIndex = 999;

            // If they are in different categories, sort by the run_order sequence
            if (catAIndex != catBIndex) {
              return catAIndex.compareTo(catBIndex);
            }

            // If they are in the SAME category, sort normally by their start number
            return a.startNo.compareTo(b.startNo);
          });

        } else {
          // Keep your existing rank sorting here
          teams = fullSortedList;
        }

        return ListView.builder(
          itemCount: teams.length,
          itemBuilder: (context, index) {
            final team = teams[index];
            int winnerRank = -1;
            var validTeams = fullSortedList.where((t) => t.category == team.category && t.bestTime > 0 && t.bestTime < 999999).toList();
            var winners = validTeams.take(3).map((t) => t.id).toList();
            winnerRank = winners.indexOf(team.id);

            return _buildTeamRow(team, winnerRank, ranks[team.category]?[team.id] ?? 0, isLandscape, settings, tp);
          },
        );
      },
    );
  }

  Widget _buildTeamRow(Team team, int winnerRank, int currentRank, bool isLandscape, RaceSettings settings, ThemeProvider tp) {
    Color catColor = team.category == "Muži" ? Colors.blue : team.category == "Ženy" ? Colors.red : Colors.purple;
    Color statusColor = Colors.grey;
    String statusText = "IDLE";

    final safeStatus = team.status.toLowerCase();

    if (safeStatus == "running") {
      statusColor = Colors.orangeAccent;
      statusText = "RUN";
    } else if (safeStatus == "preparing") {
      statusColor = Colors.lightBlueAccent;
      statusText = "PREP";
    } else if (safeStatus == "waiting") {
      statusColor = Colors.amber;
      statusText = "WAIT";
    } else if (safeStatus == "done" || team.bestTime > 0) {
      statusColor = Colors.greenAccent;
      statusText = "DONE";
    }

    Color? rowBg;
    if (winnerRank == 0) rowBg = const Color(0xFFD4AF37).withOpacity(tp.isDarkMode ? 0.15 : 0.3);
    else if (winnerRank == 1) rowBg = const Color(0xFFC0C0C0).withOpacity(tp.isDarkMode ? 0.15 : 0.3);
    else if (winnerRank == 2) rowBg = const Color(0xFFCD7F32).withOpacity(tp.isDarkMode ? 0.15 : 0.3);

    Color defaultTextColor = tp.isDarkMode ? Colors.white : Colors.black87;

    return Container(
      padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 8),
      decoration: BoxDecoration(
        color: rowBg,
        border: Border(bottom: BorderSide(color: tp.isDarkMode ? Colors.white12 : Colors.black12, width: 0.5)),
      ),
      child: Row(
        children: [
          SizedBox(width: 40, child: Text(statusText, style: TextStyle(color: statusColor, fontWeight: FontWeight.bold, fontSize: 9))),
          SizedBox(width: 25, child: Text('${team.startNo}', style: TextStyle(color: defaultTextColor, fontSize: 13))),

          if (isLandscape) ...[
            SizedBox(width: 30, child: Text(currentRank > 0 ? '$currentRank' : '-', style: TextStyle(color: defaultTextColor, fontSize: 12, fontWeight: FontWeight.bold), textAlign: TextAlign.center)),
            SizedBox(width: 30, child: Text(team.category.substring(0, 1), style: TextStyle(color: catColor, fontSize: 12, fontWeight: FontWeight.w500), textAlign: TextAlign.center)),
          ],

          Expanded(child: Text(team.name, style: TextStyle(color: defaultTextColor, fontWeight: FontWeight.bold, fontSize: isLandscape ? 14 : 12), overflow: TextOverflow.ellipsis)),
          SizedBox(width: 75, child: Text(team.formattedTime, style: TextStyle(color: Theme.of(context).colorScheme.primary, fontWeight: FontWeight.bold, fontSize: 14), textAlign: TextAlign.center)),

          if (isLandscape) ..._buildRowLanes(team, settings, defaultTextColor),
        ],
      ),
    );
  }

  void _showToast(BuildContext context, String message, Color color, IconData icon) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            Icon(icon, color: Colors.white),
            const SizedBox(width: 10),
            Expanded(child: Text(message, style: const TextStyle(fontWeight: FontWeight.bold))),
          ],
        ),
        backgroundColor: color,
        duration: const Duration(seconds: 4),
        behavior: SnackBarBehavior.floating,
        margin: const EdgeInsets.only(bottom: 20.0, left: 20.0, right: 20.0),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      ),
    );
  }
}