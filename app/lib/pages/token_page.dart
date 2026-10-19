import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:tsukena/core/api_config.dart';
import 'package:tsukena/pages/home_page.dart';

/// アプリ用のトークンを入力してもらう画面。初めて開いたときと、401 が返ったときに出す。
class TokenPage extends StatefulWidget {
  const TokenPage({super.key});

  @override
  State<TokenPage> createState() => _TokenPageState();
}

class _TokenPageState extends State<TokenPage> {
  final _controller = TextEditingController();
  String? _error;
  bool _checking = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final token = _controller.text.trim();
    if (token.isEmpty) return;
    setState(() {
      _checking = true;
      _error = null;
    });

    // 保存する前に、API で使えるトークンかを確かめる。違うトークンを保存すると、どの画面も読めなくなる
    String? error;
    try {
      final response = await http.get(
        Uri.parse('${ApiConfig.baseUrl}/categories'),
        headers: {'Authorization': 'Bearer $token'},
      );
      if (response.statusCode == 401 || response.statusCode == 403) {
        error = 'トークンが違います';
      } else if (response.statusCode != 200) {
        error = 'API に接続できませんでした（${response.statusCode}）';
      }
    } catch (_) {
      error = 'API に接続できませんでした';
    }

    if (!mounted) return;
    if (error != null) {
      setState(() {
        _checking = false;
        _error = error;
      });
      return;
    }
    await ApiConfig.saveToken(token);
    if (!mounted) return;
    Navigator.of(context).pushReplacement(
      MaterialPageRoute<void>(builder: (_) => const HomePage()),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 400),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  'Tsukena',
                  style: Theme.of(context).textTheme.headlineMedium,
                ),
                const SizedBox(height: 8),
                const Text(
                  'アプリ用のトークン（TSUKENA_APP_API_TOKEN）を入力してください。'
                  'この端末のブラウザに保存されます。',
                ),
                const SizedBox(height: 24),
                TextField(
                  controller: _controller,
                  obscureText: true,
                  autofocus: true,
                  decoration: InputDecoration(
                    labelText: 'トークン',
                    border: const OutlineInputBorder(),
                    errorText: _error,
                  ),
                  onSubmitted: (_) => _save(),
                ),
                const SizedBox(height: 16),
                FilledButton(
                  onPressed: _checking ? null : _save,
                  child: Text(_checking ? '確かめています…' : '保存する'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
