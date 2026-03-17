import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:fluttertoast/fluttertoast.dart';
import 'screen1.dart';
import 'screen2.dart';

void main() {
  runApp(const MyApp());
}

class MyCustomScrollBehavior extends MaterialScrollBehavior {
  @override
  Set<PointerDeviceKind> get dragDevices => {
        PointerDeviceKind.touch,
        PointerDeviceKind.mouse,
        PointerDeviceKind.trackpad,
      };
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Swipe App',
      scrollBehavior: MyCustomScrollBehavior(),
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
        useMaterial3: true,
        scaffoldBackgroundColor: const Color(0xFFF8FAFF),
      ),
      home: const MainSwiper(),
    );
  }
}

class MainSwiper extends StatefulWidget {
  const MainSwiper({super.key});

  @override
  State<MainSwiper> createState() => _MainSwiperState();
}

class _MainSwiperState extends State<MainSwiper> {
  final PageController _pageController = PageController();
  String _sharedText = "";

  void _onPageChanged(int index) {
    Fluttertoast.showToast(
      msg: "Current Page: ${index + 1}",
      toastLength: Toast.LENGTH_SHORT,
      gravity: ToastGravity.BOTTOM,
      timeInSecForIosWeb: 2,
      backgroundColor: Colors.green, // Green background for Android/iOS
      textColor: Colors.white,
      fontSize: 16.0,
      // Green background for Web
      webBgColor: "#4CAF50", 
      webPosition: "center", // Moved back to bottom for a more standard toast feel
      webShowClose: false,
    );
  }

  void _handleDataFromScreen1(String text) {
    setState(() {
      _sharedText = text;
    });
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () {
        FocusScopeNode currentFocus = FocusScope.of(context);
        if (!currentFocus.hasPrimaryFocus) {
          currentFocus.unfocus();
        }
      },
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Swipe Application'),
          backgroundColor: Colors.blue[100],
        ),
        body: PageView(
          controller: _pageController,
          onPageChanged: _onPageChanged,
          physics: const BouncingScrollPhysics(),
          children: [
            Screen1(onSend: _handleDataFromScreen1),
            Screen2(receivedText: _sharedText),
          ],
        ),
      ),
    );
  }
}
