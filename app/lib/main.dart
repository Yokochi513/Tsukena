import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:tsukena/core/api_config.dart';
import 'package:tsukena/core/api_http.dart';
import 'package:tsukena/pages/home_page.dart';
import 'package:tsukena/pages/token_page.dart';

Future<void> main() async {
  ApiConfig.ensureConfigured();
  // 保存したトークンを読むために、runApp の前にプラグインを使えるようにする
  WidgetsFlutterBinding.ensureInitialized();
  await ApiConfig.load();
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  // This widget is the root of your application.
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Tsukena',
      debugShowCheckedModeBanner: false,
      navigatorKey: navigatorKey,
      home: ApiConfig.hasToken ? const HomePage() : const TokenPage(),
      scrollBehavior: const MaterialScrollBehavior().copyWith(
        dragDevices: {
          PointerDeviceKind.touch,
          PointerDeviceKind.mouse,
          PointerDeviceKind.trackpad,
        },
      ),
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.teal),
        scaffoldBackgroundColor: Colors.white,
        appBarTheme: const AppBarTheme(
          backgroundColor: Colors.white,
          foregroundColor: Colors.black,
          // スクロールしたときに AppBar へ色が乗らないようにする
          surfaceTintColor: Colors.transparent,
        ),
        navigationBarTheme: const NavigationBarThemeData(
          backgroundColor: Colors.white,
        ),
      ),
    );
  }
}
