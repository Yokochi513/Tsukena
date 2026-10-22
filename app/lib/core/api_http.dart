import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:tsukena/core/api_config.dart';
import 'package:tsukena/pages/token_page.dart';

// 401 のときに、どの画面からでもトークンの入力画面に戻すために使う
final navigatorKey = GlobalKey<NavigatorState>();

/// API を呼ぶ。トークンのヘッダーを付け、401 が返ったらトークンを消して入力画面に戻す。
///
/// 各 Service は http を直接呼ばず、これを通す。
class ApiHttp {
  ApiHttp._();

  static Future<http.Response> get(Uri uri) =>
      _send(() => http.get(uri, headers: ApiConfig.headers));

  static Future<http.Response> post(Uri uri, {Object? body}) =>
      _send(() => http.post(uri, headers: ApiConfig.headers, body: body));

  static Future<http.Response> put(Uri uri, {Object? body}) =>
      _send(() => http.put(uri, headers: ApiConfig.headers, body: body));

  static Future<http.Response> patch(Uri uri, {Object? body}) =>
      _send(() => http.patch(uri, headers: ApiConfig.headers, body: body));

  static Future<http.Response> delete(Uri uri) =>
      _send(() => http.delete(uri, headers: ApiConfig.headers));

  static Future<http.Response> _send(
    Future<http.Response> Function() request,
  ) async {
    final response = await request();
    if (response.statusCode == 401) {
      // トークンが違う、または作り直された。保存したものを消して入れ直してもらう
      await ApiConfig.clearToken();
      navigatorKey.currentState?.pushAndRemoveUntil(
        MaterialPageRoute<void>(builder: (_) => const TokenPage()),
        (_) => false,
      );
    }
    return response;
  }
}
