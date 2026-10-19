class ApiConfig {
  ApiConfig._();

  // ビルドするときに --dart-define で渡す。ソースには値を書かない
  static const baseUrl = String.fromEnvironment('API_BASE_URL');
  static const token = String.fromEnvironment('API_TOKEN');

  static Map<String, String> get headers => {
    'Authorization': 'Bearer $token',
    'Content-Type': 'application/json',
  };

  static void ensureConfigured() {
    final missing = [
      if (baseUrl.isEmpty) 'API_BASE_URL',
      if (token.isEmpty) 'API_TOKEN',
    ];
    if (missing.isNotEmpty) {
      throw StateError(
        '${missing.join('、')} が設定されていません。'
        'flutter run --dart-define-from-file=dart_defines.json で起動してください',
      );
    }
  }
}
