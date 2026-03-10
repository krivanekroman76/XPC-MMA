import 'package:flutter/material.dart';

class Screen2 extends StatefulWidget {
  final String receivedText;

  const Screen2({super.key, required this.receivedText});

  @override
  State<Screen2> createState() => _Screen2State();
}

class _Screen2State extends State<Screen2> {
  late TextEditingController _controller;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: widget.receivedText);
  }

  @override
  void didUpdateWidget(Screen2 oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.receivedText != widget.receivedText) {
      _controller.text = widget.receivedText;
    }
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
          const Text('Screen 2', style: TextStyle(fontSize: 24)),
          const SizedBox(height: 20),
          TextField(
            controller: _controller,
            readOnly: true,
            decoration: const InputDecoration(
              border: OutlineInputBorder(),
              labelText: 'Received text',
            ),
          ),
        ],
      ),
    );
  }
}
