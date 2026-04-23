import 'dart:html' as html;
import 'dart:js' as js;
import 'package:flutter/foundation.dart';

/// Checks if the AwesomeNotifications JS bridge is present.
bool isAwesomeJsBridgeLoaded() {
  return js.context['AwesomeNotifications'] != null || 
         js.context['awesome_notifications'] != null;
}

/// Manually injects the required JS bridge for AwesomeNotifications.
Future<void> injectAwesomeScript() async {
  if (isAwesomeJsBridgeLoaded()) return;

  debugPrint('Injecting AwesomeNotifications JS Bridge...');
  final html.ScriptElement script = html.ScriptElement()
    ..src = "https://cdn.jsdelivr.net/gh/rafaelsetragni/awesome_notifications@master/web/awesome_notifications.js"
    ..type = 'text/javascript'
    ..async = true;

  html.document.head!.append(script);
  
  // Wait for the script to load
  await script.onLoad.first.timeout(const Duration(seconds: 5), onTimeout: () {
    debugPrint('Script injection timed out.');
    return null;
  });
}

void checkWebDiagnostics() {
  if (kIsWeb) {
    debugPrint('WEB DIAGNOSTIC:');
    debugPrint(' - Secure Context: ${html.window.isSecureContext}');
    debugPrint(' - Notification Support: ${html.Notification.supported}');
    debugPrint(' - JS Bridge Loaded: ${isAwesomeJsBridgeLoaded()}');
  }
}

void triggerNativeWebNotification() async {
  if (!html.Notification.supported) {
    debugPrint('Notifications not supported in this browser.');
    return;
  }

  String permission = html.Notification.permission;
  if (permission == 'granted') {
    html.Notification('Native Pop-up', body: 'This works even without the plugin.');
  } else if (permission == 'default') {
    debugPrint('Requesting native permission...');
    // html.Notification.requestPermission() handles the Promise automatically in Dart
    final result = await html.Notification.requestPermission();
    debugPrint('Native Permission Result: $result');
  } else {
    debugPrint('Permission denied. Please reset in browser settings.');
  }
}
