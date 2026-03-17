import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

import 'urls.dart';
import 'note.dart';
import 'create.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Django Notes',
      debugShowCheckedModeBanner: false, // Skryje ten červený "DEBUG" pruh
      theme: ThemeData(
        // Použití moderního Material 3 designu a vygenerování palety z jedné barvy
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
        useMaterial3: true, 
        appBarTheme: const AppBarTheme(
          centerTitle: true,
          elevation: 0, // Plochý a moderní vzhled hlavičky
        ),
      ),
      home: const HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  List notes = [];
  bool isLoading = true;
  bool isError = false; // Proměnná pro sledování chyby sítě

  @override
  void initState() {
    super.initState();
    fetchNotes();
  }

  Future<void> fetchNotes() async {
    setState(() {
      isLoading = true;
      isError = false;
    });

    try {
      final response = await http.get(Uri.parse(ApiUrls.notes));
      if (response.statusCode == 200) {
        setState(() {
          notes = json.decode(response.body);
          isLoading = false;
        });
      } else {
        throw Exception('Server vrátil chybu ${response.statusCode}');
      }
    } catch (e) {
      debugPrint("Chyba při načítání: $e");
      setState(() {
        isLoading = false;
        isError = true; // Zastavíme načítání a zaznamenáme chybu
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey[100], // Jemné šedé pozadí pro lepší kontrast karet
      appBar: AppBar(
        title: const Text('Moje poznámky', style: TextStyle(fontWeight: FontWeight.bold)),
        backgroundColor: Theme.of(context).colorScheme.primary,
        foregroundColor: Theme.of(context).colorScheme.onPrimary,
      ),
      body: _buildBody(),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () {
          Navigator.push(
            context,
            MaterialPageRoute(builder: (context) => const CreatePage()),
          ).then((_) => fetchNotes());
        },
        backgroundColor: Theme.of(context).colorScheme.primary,
        foregroundColor: Theme.of(context).colorScheme.onPrimary,
        icon: const Icon(Icons.add),
        label: const Text('Nová', style: TextStyle(fontWeight: FontWeight.bold)),
      ),
    );
  }

  // Pomocná metoda pro vyčištění struktury `build`
  Widget _buildBody() {
    if (isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (isError) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.wifi_off, size: 64, color: Colors.grey),
            const SizedBox(height: 16),
            const Text('Nepodařilo se načíst data.', style: TextStyle(fontSize: 18)),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: fetchNotes, // Tlačítko pro opakování pokusu
              icon: const Icon(Icons.refresh),
              label: const Text('Zkusit znovu'),
            )
          ],
        ),
      );
    }

    if (notes.isEmpty) {
      return const Center(
        child: Text('Zatím tu nemáš žádné poznámky.', style: TextStyle(fontSize: 16)),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.only(top: 16, bottom: 80), // Místo dole kvůli tlačítku
      itemCount: notes.length,
      itemBuilder: (context, index) {
        final note = notes[index];
        return Card(
          margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          elevation: 2, // Lehký stín
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12), // Zaoblené rohy
          ),
          child: ListTile(
            contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
            title: Text(
              note['body'] ?? 'Prázdná poznámka',
              maxLines: 2, // Omezí text na dva řádky
              overflow: TextOverflow.ellipsis, // Přidá tři tečky, pokud je text delší
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w500),
            ),
            trailing: Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.primary.withOpacity(0.1), // Jemné podbarvení šipky
                shape: BoxShape.circle,
              ),
              child: Icon(
                Icons.chevron_right, 
                color: Theme.of(context).colorScheme.primary
              ),
            ),
            onTap: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => NotePage(noteId: note['id']),
                ),
              ).then((_) => fetchNotes());
            },
          ),
        );
      },
    );
  }
}