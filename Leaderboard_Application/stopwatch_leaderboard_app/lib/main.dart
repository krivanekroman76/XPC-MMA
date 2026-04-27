import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart'; // NEW: Added this import
import 'firebase_options.dart';
import 'welcome_screen.dart';
import 'theme_provider.dart';
import 'firebase_service.dart';

final GlobalKey<NavigatorState> navigatorKey = GlobalKey<NavigatorState>();

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );

  // Initialize your service and load saved subscription states
  final firebaseService = FirebaseService();
  firebaseService.setNavigatorKey(navigatorKey);
  await firebaseService.initNotifications(); // <--- ADD THIS LINE

  final prefs = await SharedPreferences.getInstance();

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => ThemeProvider(prefs)),
      ],
      child: const MyApp(),
    ),
  );
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    final themeProvider = Provider.of<ThemeProvider>(context);

    return MaterialApp(
      title: themeProvider.translateKey('app_title'),
      navigatorKey: navigatorKey,
      debugShowCheckedModeBanner: false,
      // FIXED: Using your actual ThemeProvider getters
      themeMode: themeProvider.isDarkMode ? ThemeMode.dark : ThemeMode.light,
      theme: ThemeData.light().copyWith(
        colorScheme: ColorScheme.light(primary: themeProvider.seedColor),
      ),
      darkTheme: ThemeData.dark().copyWith(
        colorScheme: ColorScheme.dark(primary: themeProvider.seedColor),
      ),
      // FIXED: Removed 'const' here to fix the constant expression error
      home: WelcomeScreen(),
    );
  }
}