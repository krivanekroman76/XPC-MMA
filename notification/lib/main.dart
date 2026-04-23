import 'package:flutter/material.dart';
import 'package:awesome_notifications/awesome_notifications.dart';
import 'package:flutter/foundation.dart';

// Conditional imports to handle web-specific JS code safely
import 'web_config_stub.dart' if (dart.library.js) 'web_config.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  debugPrint('--- [START] Notification App Initialization ---');

  if (kIsWeb) {
    // Attempt to manually inject the JS script if it's missing from index.html
    await injectAwesomeScript();
    
    // Wait for the JS bridge to become ready
    int retries = 0;
    while (!isAwesomeJsBridgeLoaded() && retries < 15) {
      debugPrint('Waiting for JS Bridge... Attempt ${retries + 1}');
      await Future.delayed(const Duration(milliseconds: 300));
      retries++;
    }
    checkWebDiagnostics();
  }

  try {
    bool isInitialized = await AwesomeNotifications().initialize(
      null,
      [
        NotificationChannel(
          channelGroupKey: 'basic_channel_group',
          channelKey: 'basic_channel',
          channelName: 'Basic notifications',
          channelDescription: 'Notification channel for basic tests',
          defaultColor: const Color(0xFF9D50BB),
          ledColor: Colors.white,
          importance: NotificationImportance.Max,
          channelShowBadge: true,
          onlyAlertOnce: true,
          playSound: true,
          criticalAlerts: true,
        )
      ],
      channelGroups: [
        NotificationChannelGroup(
          channelGroupKey: 'basic_channel_group',
          channelGroupName: 'Basic group',
        )
      ],
      debug: true,
    );
    debugPrint('AwesomeNotifications Plugin initialized: $isInitialized');
  } catch (e) {
    debugPrint('Plugin Initialization Error: $e');
  }

  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Flutter Notifications',
      theme: ThemeData(colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple), useMaterial3: true),
      home: const MyHomePage(title: 'Notification Home Page'),
    );
  }
}

class MyHomePage extends StatefulWidget {
  const MyHomePage({super.key, required this.title});
  final String title;
  @override
  State<MyHomePage> createState() => _MyHomePageState();
}

class _MyHomePageState extends State<MyHomePage> {
  bool _isAllowed = false;

  @override
  void initState() {
    super.initState();
    _checkPermission();
    
    AwesomeNotifications().setListeners(
      onActionReceivedMethod: NotificationController.onActionReceivedMethod,
      onNotificationCreatedMethod: NotificationController.onNotificationCreatedMethod,
      onNotificationDisplayedMethod: NotificationController.onNotificationDisplayedMethod,
      onDismissActionReceivedMethod: NotificationController.onDismissActionReceivedMethod,
    );
  }

  Future<void> _checkPermission() async {
    _isAllowed = await AwesomeNotifications().isNotificationAllowed();
    debugPrint('Initial permission status (via plugin): $_isAllowed');
    if (mounted) setState(() {});
  }

  Future<void> _requestPermission() async {
    debugPrint('Step 1: Requesting Permission via Plugin...');
    bool granted = await AwesomeNotifications().requestPermissionToSendNotifications();
    debugPrint('Plugin Permission Result: $granted');
    setState(() => _isAllowed = granted);
  }

  void _triggerPluginNotification() async {
    debugPrint('Step 2: Triggering via Plugin...');
    try {
      bool isCreated = await AwesomeNotifications().createNotification(
        content: NotificationContent(
          id: 10,
          channelKey: 'basic_channel',
          title: 'System Notification!',
          body: 'This should appear as a pop-up and on your lock screen.',
          notificationLayout: NotificationLayout.Default,
          wakeUpScreen: true,
          fullScreenIntent: true,
          criticalAlert: true,
          category: NotificationCategory.Message,
        ),
      );
      debugPrint('Plugin Created: $isCreated');
    } catch (e) {
      debugPrint('Plugin Trigger Error: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        title: Text(widget.title),
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(20.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(_isAllowed ? Icons.verified : Icons.warning, color: _isAllowed ? Colors.green : Colors.red, size: 50),
              Text(
                'Plugin Status: ${_isAllowed ? "READY" : "DENIED / NOT INITIALIZED"}',
                style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 30),
              ElevatedButton.icon(
                onPressed: _requestPermission,
                icon: const Icon(Icons.security),
                label: const Text('1. Request Permission (Plugin)'),
              ),
              const SizedBox(height: 10),
              ElevatedButton.icon(
                onPressed: _triggerPluginNotification,
                icon: const Icon(Icons.notifications_active),
                label: const Text('2. Trigger (Plugin)'),
              ),
              const Divider(height: 40),
              const Text('Web Troubleshooting:', style: TextStyle(fontWeight: FontWeight.bold)),
              const SizedBox(height: 10),
              ElevatedButton(
                onPressed: () => triggerNativeWebNotification(),
                style: ElevatedButton.styleFrom(backgroundColor: Colors.orange),
                child: const Text('3. Test Native JS (Diagnostic)'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class NotificationController {
  @pragma("vm:entry-point")
  static Future<void> onNotificationCreatedMethod(ReceivedNotification receivedNotification) async {
    debugPrint('Notification Created: ${receivedNotification.id}');
  }
  @pragma("vm:entry-point")
  static Future<void> onNotificationDisplayedMethod(ReceivedNotification receivedNotification) async {
    debugPrint('Notification Displayed: ${receivedNotification.id}');
  }
  @pragma("vm:entry-point")
  static Future<void> onDismissActionReceivedMethod(ReceivedAction receivedAction) async {
    debugPrint('Notification Dismissed: ${receivedAction.id}');
  }
  @pragma("vm:entry-point")
  static Future<void> onActionReceivedMethod(ReceivedAction receivedAction) async {
    debugPrint('Notification Action Received: ${receivedAction.id}');
  }
}
