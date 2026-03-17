import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

import '../urls.dart';

class UpdatePage extends StatefulWidget {
  final Map note; // Přijme objekt poznámky z detailu
  const UpdatePage({super.key, required this.note});

  @override
  State<UpdatePage> createState() => _UpdatePageState();
}

class _UpdatePageState extends State<UpdatePage> {
  late TextEditingController _controller;

  @override
  void initState() {
    super.initState();
    // Předvyplní pole aktuálním textem
    _controller = TextEditingController(text: widget.note['body']); 
  }

  Future<void> updateNote() async {
    await http.put(
      Uri.parse(ApiUrls.noteDetail(widget.note['id'])),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({'body': _controller.text}),
    );
    
    if (mounted) Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Upravit poznámku')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            TextField(
              controller: _controller,
              decoration: const InputDecoration(
                hintText: 'Uprav text...',
                border: OutlineInputBorder(),
              ),
              maxLines: 5,
            ),
            const SizedBox(height: 20),
            ElevatedButton(
              onPressed: updateNote,
              child: const Text('Uložit změny'),
            )
          ],
        ),
      ),
    );
  }
}