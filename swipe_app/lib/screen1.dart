import 'package:flutter/material.dart';

class Screen1 extends StatefulWidget {
  final Function(String) onSend;

  const Screen1({super.key, required this.onSend});

  @override
  State<Screen1> createState() => _Screen1State();
}

class _Screen1State extends State<Screen1> {
  final TextEditingController _controller = TextEditingController();

  void _handleSend() {
    final text = _controller.text;
    widget.onSend(text);
    _controller.clear();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Text('Screen 1', style: TextStyle(fontSize: 24)),
          const SizedBox(height: 20),
          TextField(
            controller: _controller,
            decoration: const InputDecoration(
              border: OutlineInputBorder(),
              labelText: 'Enter text',
            ),
          ),
          const SizedBox(height: 20),
          ElevatedButton(
            onPressed: _handleSend,
            child: const Text('Send to Screen 2'),
          ),
        ],
      ),
    );
  }
}
