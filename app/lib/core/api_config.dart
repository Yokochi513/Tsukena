import 'package:shared_preferences/shared_preferences.dart';

class ApiConfig {
  ApiConfig._();

  // ビルドするときに --dart-define で渡す。秘密ではないので、公開するビルドに入ってよい
  static const baseUrl = String.fromEnvironment('API_BASE_URL');

  // トークンはビルドに入れず、アプリの画面で入力してブラウザに保存する（→ ADR-0010）。
  // Web 版は GitHub Pages で誰でも読める場所に置くため、ビルドに入れると公開されてしまう。
  // 開発のときだけ、dart_defines.json の API_TOKEN を初期値として使える
  static const _devToken = String.fromEnvironment('API_TOKEN');
  static const _tokenKey = 'api_token';
  static String _token = '';

  static bool get hasToken => _token.isNotEmpty;

  static Map<String, String> get headers => {
    'Authorization': 'Bearer $_token',
    'Content-Type': 'application/json',
  };

  static void ensureConfigured() {
    if (baseUrl.isEmpty) {
      throw StateError(
        'API_BASE_URL が設定されていません。'
        'flutter run --dart-define-from-file=dart_defines.json で起動してください',
      );
    }
  }

  /// 起動するときに main() から呼ぶ。保存したトークンを読み込む。
  static Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    _token = prefs.getString(_tokenKey) ?? _devToken;
  }

  static Future<void> saveToken(String token) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_tokenKey, token);
    _token = token;
  }

  static Future<void> clearToken() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_tokenKey);
    _token = '';
  }
}
