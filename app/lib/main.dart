import 'package:flutter/material.dart';
import 'package:tsukena/core/api_config.dart';
import 'package:tsukena/pages/home_page.dart';

void main() {
  ApiConfig.ensureConfigured();
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
      home: const HomePage(),
    );
  }
}
