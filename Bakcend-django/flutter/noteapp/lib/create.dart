import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

import '../../urls.dart';

class CreatePage extends StatefulWidget {
  const CreatePage({super.key});

  @override
  State<CreatePage> createState() => _CreatePageState();
}

class _CreatePageState extends State<CreatePage> {
  final TextEditingController _controller = TextEditingController();

  Future<void> createNote() async {
    if (_controller.text.isEmpty) return;

    await http.post(
      Uri.parse(ApiUrls.notes),
      headers: {'Content-Type': 'application/json'},
      // Převod do JSON formátu, který Django očekává
      body: json.encode({'body': _controller.text}), 
    );
    
    if (mounted) Navigator.pop(context); // Zavře stránku a vrátí tě na seznam
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Nová poznámka')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            TextField(
              controller: _controller,
              decoration: const InputDecoration(
                hintText: 'Napiš něco chytrého...',
                border: OutlineInputBorder(),
              ),
              maxLines: 5,
            ),
            const SizedBox(height: 20),
            ElevatedButton(
              onPressed: createNote,
              child: const Text('Vytvořit'),
            )
          ],
        ),
      ),
    );
  }
}