import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'firebase_service.dart';
import 'team_model.dart';
import 'welcome_screen.dart';
import 'dart:async';
import 'theme_provider.dart';

enum SortType { rank, startNo }

class RaceLeaderboard extends StatefulWidget {
  final String initialRace;
  const RaceLeaderboard({super.key, required this.initialRace});

  @override
  State<RaceLeaderboard> createState() => _RaceLeaderboardState();
}

class _RaceLeaderboardState extends State<RaceLeaderboard> {
  late String selectedRace;
  String selectedCategory = "Vše";
  SortType currentSort = SortType.rank;

  @override
  void initState() {
    super.initState();
    selectedRace = widget.initialRace;
  }

  // Funkce na překlad filtrů kategorií (Firebase potřebuje český klíč, my měníme jen co vidí uživatel)
  String getTranslatedCategory(String cat, ThemeProvider tp) {
    if (cat == "Vše") return tp.translate("Vše", "All");
    if (cat == "Muži") return tp.translate("Muži", "Men");
    if (cat == "Ženy") return tp.translate("Ženy", "Women");
    if (cat == "Dorost") return tp.translate("Dorost", "Youth");
    return cat;
  }

  @override
  Widget build(BuildContext context) {
    bool isSubscribed = FirebaseService().isRaceNotificationEnabled(selectedRace);
    bool isMasterOn = FirebaseService().isMasterNotificationEnabled;
    final themeProvider = Provider.of<ThemeProvider>(context);
    final colorScheme = Theme.of(context).colorScheme;

    return OrientationBuilder(
      builder: (context, orientation) {
        final bool isLandscape = orientation == Orientation.landscape;

        return Scaffold(
          // ODSTRANĚNA TVRDÁ ČERNÁ, POUŽIJE SE BARVA TÉMATU
          appBar: AppBar(
            title: Text(selectedRace, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
            elevation: 0,
            actions: [
              // Výběr barvy
              PopupMenuButton<Color>(
                icon: const Icon(Icons.palette),
                onSelected: (color) => themeProvider.setColor(color),
                itemBuilder: (context) => themeProvider.availableColors.map((color) => PopupMenuItem(
                  value: color,
                  child: Container(width: 24, height: 24, decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
                )).toList(),
              ),
              TextButton(
                onPressed: () => themeProvider.toggleLanguage(),
                child: Text(
                  themeProvider.locale.languageCode.toUpperCase(),
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: themeProvider.isDarkMode ? Colors.white : colorScheme.primary),
                ),
              ),
              IconButton(
                icon: Icon(themeProvider.isDarkMode ? Icons.light_mode : Icons.dark_mode),
                onPressed: () => themeProvider.toggleTheme(),
              ),
              StreamBuilder<RaceSettings>(
                  stream: FirebaseService().getSettingsStream(selectedRace),
                  builder: (context, snapshot) {
                    bool isFinished = snapshot.data?.isFinished ?? false;
                    if (isFinished) return const SizedBox();

                    if (isMasterOn) {
                      return IconButton(
                        icon: Icon(Icons.notifications_active, color: colorScheme.primary),
                        onPressed: () {
                          ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(themeProvider.translate('Už odebíráte všechny závody.', 'You are already subscribed to all.'))));
                        },
                      );
                    }

                    return IconButton(
                      icon: Icon(
                        isSubscribed ? Icons.notifications_active : Icons.notifications_none,
                        color: isSubscribed ? colorScheme.primary : (themeProvider.isDarkMode ? Colors.white70 : Colors.black54),
                      ),
                      onPressed: () async {
                        if (!isSubscribed) {
                          bool success = await FirebaseService().init();
                          if (!success) return;
                        }
                        await FirebaseService().setRaceNotification(selectedRace, !isSubscribed);
                        setState(() {});
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
              stream: FirebaseService().getSettingsStream(selectedRace),
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
              child: Text(tp.translate('XPC-MMA\nZávody', 'XPC-MMA\nRaces'), style: const TextStyle(color: Colors.white, fontSize: 24), textAlign: TextAlign.center),
            ),
          ),
          ListTile(
            leading: const Icon(Icons.home),
            title: Text(tp.translate('Hlavní menu', 'Main Menu')),
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
              stream: FirebaseService().getRacesStream(),
              builder: (context, snapshot) {
                final races = snapshot.data ?? FirebaseService().currentRaces;
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
          SizedBox(width: 40, child: Text(tp.translate('ST', 'ST'), style: TextStyle(color: textColor, fontWeight: FontWeight.bold, fontSize: 10))),
          SizedBox(width: 25, child: Text('#', style: TextStyle(color: textColor, fontWeight: FontWeight.bold, fontSize: 10))),
          if (isLandscape) ...[
            SizedBox(width: 30, child: Text('Pos', style: TextStyle(color: textColor, fontWeight: FontWeight.bold, fontSize: 10), textAlign: TextAlign.center)),
            SizedBox(width: 30, child: Text('Cat', style: TextStyle(color: textColor, fontWeight: FontWeight.bold, fontSize: 10), textAlign: TextAlign.center)),
          ],
          Expanded(child: Text(tp.translate('TÝM', 'TEAM'), style: TextStyle(color: textColor, fontWeight: FontWeight.bold, fontSize: 10))),
          SizedBox(width: 75, child: Text(tp.translate('VÝSLEDEK', 'RESULT'), style: TextStyle(color: textColor, fontWeight: FontWeight.bold, fontSize: 10), textAlign: TextAlign.center)),
          if (isLandscape) ..._buildHeaderLanes(settings, textColor),
        ],
      ),
    );
  }

  List<Widget> _buildHeaderLanes(RaceSettings settings, Color textColor) {
    List<Widget> widgets = [];
    for (int i = 0; i < settings.attemptsCount; i++) {
      for (int j = 0; j < settings.lanesCount; j++) {
        String label = settings.attemptsCount > 1 ? '${i+1}L${j+1}' : 'L${j+1}';
        widgets.add(SizedBox(width: 42, child: Text(label, style: TextStyle(color: textColor, fontSize: 8), textAlign: TextAlign.center)));
      }
      String resLabel = 'A${i+1}';
      widgets.add(SizedBox(width: 45, child: Text(resLabel, style: TextStyle(color: textColor, fontSize: 8), textAlign: TextAlign.center)));
    }
    return widgets;
  }

  Widget _buildTeamList(bool isLandscape, RaceSettings settings, ThemeProvider tp) {
    return StreamBuilder<List<Team>>(
      key: ValueKey('$selectedRace-$selectedCategory'),
      stream: selectedCategory == "Vše"
          ? _getMergedStream(selectedRace)
          : FirebaseService().getTeamsStream(selectedRace, selectedCategory),
      builder: (context, snapshot) {
        if (!snapshot.hasData) return const Center(child: CircularProgressIndicator());
        var teams = snapshot.data!;
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
          ranks[cat] = { for (var i = 0; i < catTeams.length; i++) catTeams[i].id : i + 1 };
        }

        if (currentSort == SortType.startNo) {
          teams.sort((a, b) => a.startNo.compareTo(b.startNo));
        } else {
          teams = fullSortedList;
        }

        return ListView.builder(
          itemCount: teams.length,
          itemBuilder: (context, index) {
            final team = teams[index];
            int winnerRank = -1;
            if (settings.isFinished) {
              var winners = fullSortedList.where((t) => t.category == team.category && t.bestTime > 0 && t.bestTime < 999999).take(3).map((t) => t.id).toList();
              winnerRank = winners.indexOf(team.id);
            }
            return _buildTeamRow(team, winnerRank, ranks[team.category]?[team.id] ?? 0, isLandscape, settings, tp);
          },
        );
      },
    );
  }

  Stream<List<Team>> _getMergedStream(String race) {
    final controller = StreamController<List<Team>>();
    Map<String, List<Team>> latestData = {};
    void update() {
      if (controller.isClosed) return;
      List<Team> all = [];
      latestData.values.forEach((list) => all.addAll(list));
      controller.add(all);
    }
    final subs = <StreamSubscription>[];
    for (var cat in ["Muži", "Ženy", "Dorost"]) {
      subs.add(FirebaseService().getTeamsStream(race, cat).listen((data) {
        latestData[cat] = data;
        update();
      }));
    }
    controller.onCancel = () { for (var s in subs) { s.cancel(); } };
    return controller.stream;
  }

  Widget _buildTeamRow(Team team, int winnerRank, int currentRank, bool isLandscape, RaceSettings settings, ThemeProvider tp) {
    Color catColor = team.category == "Muži" ? Colors.blue : team.category == "Ženy" ? Colors.red : Colors.purple;
    Color statusColor = Colors.grey;
    String statusText = "IDLE";

    if (team.status == "running") {
      statusColor = Colors.orangeAccent;
      statusText = "RUN";
    } else if (team.status == "preparing") {
      statusColor = Colors.lightBlueAccent;
      statusText = "PREP";
    } else if (team.status == "waiting") {
      statusColor = Colors.amber;
      statusText = "WAIT";
    } else if (team.status == "done" || team.bestTime > 0) {
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

  List<Widget> _buildRowLanes(Team team, RaceSettings settings, Color textColor) {
    List<Widget> widgets = [];
    for (int i = 0; i < settings.attemptsCount; i++) {
      for (int j = 0; j < settings.lanesCount; j++) {
        widgets.add(SizedBox(width: 42, child: Text(team.getRunLaneTime(i, j), style: TextStyle(color: textColor.withOpacity(0.7), fontSize: 11), textAlign: TextAlign.center)));
      }
      widgets.add(SizedBox(width: 45, child: Text(team.getRunFinalTime(i), style: TextStyle(color: textColor.withOpacity(0.7), fontSize: 11), textAlign: TextAlign.center)));
    }
    return widgets;
  }
}