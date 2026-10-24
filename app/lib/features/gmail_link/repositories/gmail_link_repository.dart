import 'dart:convert';

import 'package:tsukena/core/api_config.dart';
import 'package:tsukena/core/api_http.dart';

/// サーバーの準備ができておらず、連携を始められない（503）。
class GmailLinkNotConfiguredException implements Exception {}

class GmailLinkService {
  // 接続先はテストで差し替えられるよう引数でも受け取る。省略すると起動時に渡した値を使う
  GmailLinkService({this.baseUrl = ApiConfig.baseUrl});

  final String baseUrl;

  /// Gmail と連携できているか（→ docs/api_list.md 2.7）。
  Future<bool> getLinked() async {
    final response = await ApiHttp.get(
      Uri.parse('$baseUrl/oauth/google/status'),
    );

    if (response.statusCode != 200) {
      throw Exception('Gmail 連携の状態の取得に失敗しました');
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    return json['linked'] as bool;
  }

  /// Google の同意画面の URL を受け取る（→ docs/api_list.md 2.7）。
  ///
  /// URL は10分で使えなくなるので、受け取ったらすぐに開く。
  Future<Uri> getAuthorizationUrl() async {
    final response = await ApiHttp.get(
      Uri.parse('$baseUrl/oauth/google/start'),
    );

    if (response.statusCode == 503) {
      throw GmailLinkNotConfiguredException();
    }
    if (response.statusCode != 200) {
      throw Exception('Gmail 連携の開始に失敗しました');
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    return Uri.parse(json['authorization_url'] as String);
  }
}
