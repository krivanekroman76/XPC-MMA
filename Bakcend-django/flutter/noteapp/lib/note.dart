import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

import '../urls.dart';
import '../update.dart';

class NotePage extends StatefulWidget {
  final int noteId;
  const NotePage({super.key, required this.noteId});

  @override
  State<NotePage> createState() => _NotePageState();
}

class _NotePageState extends State<NotePage> {
  Map? note;

  @override
  void initState() {
    super.initState();
    fetchNote();
  }

  Future<void> fetchNote() async {
    final response = await http.get(Uri.parse(ApiUrls.noteDetail(widget.noteId)));
    if (response.statusCode == 200) {
      setState(() {
        note = json.decode(response.body);
      });
    }
  }

  Future<void> deleteNote() async {
    await http.delete(Uri.parse(ApiUrls.noteDetail(widget.noteId)));
    if (mounted) Navigator.pop(context); // Návrat zpět po smazání
  }

  @override
  Widget build(BuildContext context) {
    if (note == null) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Detail'),
        actions: [
          IconButton(
            icon: const Icon(Icons.edit),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => UpdatePage(note: note!)),
              ).then((_) => fetchNote()); // Obnoví data po úspěšné editaci
            },
          ),
          IconButton(
            icon: const Icon(Icons.delete),
            onPressed: deleteNote,
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Text(
          note!['body'] ?? '',
          style: const TextStyle(fontSize: 18),
        ),
      ),
    );
  }
}