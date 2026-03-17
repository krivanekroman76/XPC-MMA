import 'package:flutter/material.dart';
import 'firebase_service.dart';
import 'team_model.dart';
import 'dart:async';
import 'welcome_screen.dart';

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
  StreamSubscription? _notificationSubscription;

  @override
  void initState() {
    super.initState();
    selectedRace = widget.initialRace;
    _setupListeners(selectedRace);
  }

  void _setupListeners(String raceName) {
    FirebaseService().startMonitoringRace(raceName);
    _notificationSubscription?.cancel();
    _notificationSubscription = FirebaseService().notifications.listen((notification) {
      if (mounted) {
        final color = notification['isNP'] ? Colors.grey : (notification['isBetter'] ? Colors.green : Colors.red);
        final msg = notification['isNP'] 
            ? "Tým ${notification['teamName']} (${notification['category']}): NP!" 
            : "Tým ${notification['teamName']} (${notification['category']}) doběhl!\nČas: ${notification['time']}";

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(msg),
            backgroundColor: color,
            duration: const Duration(seconds: 5),
          ),
        );
      }
    });
  }

  @override
  void dispose() {
    _notificationSubscription?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF121212),
      appBar: AppBar(
        title: Text(selectedRace, style: const TextStyle(fontWeight: FontWeight.bold)),
        backgroundColor: Colors.black,
        elevation: 0,
        actions: [
          IconButton(
            icon: Icon(currentSort == SortType.rank ? Icons.emoji_events : Icons.list),
            onPressed: () => setState(() => currentSort =
            currentSort == SortType.rank ? SortType.startNo : SortType.rank),
          ),
        ],
      ),
      drawer: Drawer(
        backgroundColor: const Color(0xFF1E1E1E),
        child: Column(
          children: [
            const DrawerHeader(
              decoration: BoxDecoration(color: Colors.black),
              child: Center(
                child: Text('XPC-MMA\nZávody', style: TextStyle(color: Colors.white, fontSize: 24), textAlign: TextAlign.center),
              ),
            ),
            ListTile(
              leading: const Icon(Icons.home, color: Colors.white70),
              title: const Text('Hlavní menu', style: TextStyle(color: Colors.white)),
              onTap: () {
                Navigator.of(context).pushAndRemoveUntil(
                  MaterialPageRoute(builder: (context) => const WelcomeScreen()),
                  (route) => false,
                );
              },
            ),
            const Divider(color: Colors.white12),
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
                        leading: const Icon(Icons.flag_rounded, color: Colors.white70),
                        title: Text(raceName, style: const TextStyle(color: Colors.white)),
                        selected: selectedRace == raceName,
                        selectedTileColor: Colors.deepPurple.withOpacity(0.3),
                        onTap: () {
                          if (selectedRace != raceName) {
                            setState(() {
                              selectedRace = raceName;
                              _setupListeners(selectedRace);
                            });
                          }
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
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 8.0),
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: ["Vše", "Muži", "Ženy", "Dorost"].map((cat) => Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 4.0),
                  child: ChoiceChip(
                    label: Text(cat),
                    selected: selectedCategory == cat,
                    onSelected: (s) {
                      if (s) setState(() => selectedCategory = cat);
                    },
                    selectedColor: Colors.deepPurple,
                    labelStyle: TextStyle(color: selectedCategory == cat ? Colors.white : Colors.white70),
                    backgroundColor: Colors.grey[900],
                  ),
                )).toList(),
              ),
            ),
          ),
          
          Container(
            padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
            color: Colors.black,
            child: const Row(
              children: [
                SizedBox(width: 50, child: Text('Status', style: TextStyle(color: Colors.grey, fontWeight: FontWeight.bold, fontSize: 11))),
                SizedBox(width: 30, child: Text('#', style: TextStyle(color: Colors.grey, fontWeight: FontWeight.bold, fontSize: 11))),
                SizedBox(width: 30, child: Text('Pos.', style: TextStyle(color: Colors.grey, fontWeight: FontWeight.bold, fontSize: 11))),
                SizedBox(width: 45, child: Text('Cat', style: TextStyle(color: Colors.grey, fontWeight: FontWeight.bold, fontSize: 11))),
                Expanded(child: Text('Team Name', style: TextStyle(color: Colors.grey, fontWeight: FontWeight.bold, fontSize: 11))),
                SizedBox(width: 90, child: Text('FINAL RESULT', style: TextStyle(color: Colors.grey, fontWeight: FontWeight.bold, fontSize: 11), textAlign: TextAlign.center)),
                SizedBox(width: 45, child: Text('P1-L1', style: TextStyle(color: Colors.grey, fontSize: 9), textAlign: TextAlign.center)),
                SizedBox(width: 45, child: Text('P1-L2', style: TextStyle(color: Colors.grey, fontSize: 9), textAlign: TextAlign.center)),
                SizedBox(width: 55, child: Text('Res 1', style: TextStyle(color: Colors.grey, fontSize: 9), textAlign: TextAlign.center)),
                SizedBox(width: 45, child: Text('P2-L1', style: TextStyle(color: Colors.grey, fontSize: 9), textAlign: TextAlign.center)),
                SizedBox(width: 45, child: Text('P2-L2', style: TextStyle(color: Colors.grey, fontSize: 9), textAlign: TextAlign.center)),
                SizedBox(width: 55, child: Text('Res 2', style: TextStyle(color: Colors.grey, fontSize: 9), textAlign: TextAlign.center)),
              ],
            ),
          ),

          Expanded(
            child: StreamBuilder<String>(
              stream: FirebaseService().getRaceStatusStream(selectedRace),
              builder: (context, statusSnapshot) {
                final isFinished = statusSnapshot.data == "finished";

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
                        int rank = -1;
                        if (isFinished) {
                           var winners = fullSortedList
                              .where((t) => t.category == team.category && t.bestTime > 0 && t.bestTime < 999999)
                              .take(3)
                              .map((t) => t.id)
                              .toList();
                          rank = winners.indexOf(team.id);
                        }
                        return _buildTeamRow(team, rank, ranks[team.category]?[team.id] ?? 0);
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

  Widget _buildTeamRow(Team team, int winnerRank, int currentRank) {
    Color catColor = team.category == "Muži" ? Colors.blue : team.category == "Ženy" ? Colors.red : Colors.purple;
    
    Color statusColor = Colors.grey;
    String statusText = "IDLE";
    if (team.status == "running") {
      statusColor = Colors.orangeAccent;
      statusText = "RUN";
    } else if (team.status == "preparing") {
      statusColor = Colors.lightBlueAccent;
      statusText = "PREP";
    } else if (team.status == "done" || team.bestTime > 0) {
      statusColor = Colors.greenAccent;
      statusText = "DONE";
    } else if (team.status == "idle") {
      statusColor = Colors.grey;
      statusText = "IDLE";
    }

    Color? rowBg;
    if (winnerRank == 0) rowBg = const Color(0xFFD4AF37).withOpacity(0.15);
    else if (winnerRank == 1) rowBg = const Color(0xFFC0C0C0).withOpacity(0.15);
    else if (winnerRank == 2) rowBg = const Color(0xFFCD7F32).withOpacity(0.15);

    return Container(
      padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
      decoration: BoxDecoration(
        color: rowBg,
        border: const Border(bottom: BorderSide(color: Colors.white12, width: 0.5)),
      ),
      child: Row(
        children: [
          SizedBox(width: 50, child: Text(statusText, style: TextStyle(color: statusColor, fontWeight: FontWeight.bold, fontSize: 11))),
          SizedBox(width: 30, child: Text('${team.startNo}', style: const TextStyle(color: Colors.white, fontSize: 13))),
          SizedBox(width: 30, child: Text(currentRank > 0 ? '$currentRank' : '-', style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold))),
          SizedBox(width: 45, child: Text(team.category, style: TextStyle(color: catColor, fontSize: 13, fontWeight: FontWeight.w500))),
          Expanded(child: Text(team.name, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14))),
          SizedBox(width: 90, child: Text(team.formattedTime, style: const TextStyle(color: Colors.amber, fontWeight: FontWeight.bold, fontSize: 15), textAlign: TextAlign.center)),
          
          SizedBox(width: 45, child: Text(team.getRunLaneTime(0, 1), style: const TextStyle(color: Colors.white70, fontSize: 12), textAlign: TextAlign.center)),
          SizedBox(width: 45, child: Text(team.getRunLaneTime(0, 2), style: const TextStyle(color: Colors.white70, fontSize: 12), textAlign: TextAlign.center)),
          SizedBox(width: 55, child: Text(team.getRunFinalTime(0), style: const TextStyle(color: Colors.white70, fontSize: 12), textAlign: TextAlign.center)),
          
          SizedBox(width: 45, child: Text(team.getRunLaneTime(1, 1), style: const TextStyle(color: Colors.white70, fontSize: 12), textAlign: TextAlign.center)),
          SizedBox(width: 45, child: Text(team.getRunLaneTime(1, 2), style: const TextStyle(color: Colors.white70, fontSize: 12), textAlign: TextAlign.center)),
          SizedBox(width: 55, child: Text(team.getRunFinalTime(1), style: const TextStyle(color: Colors.white70, fontSize: 12), textAlign: TextAlign.center)),
        ],
      ),
    );
  }
}
