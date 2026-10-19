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
    );
  }
}
