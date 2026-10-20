import 'dart:convert';

import 'package:tsukena/core/api_config.dart';
import 'package:tsukena/core/api_http.dart';
import 'package:tsukena/features/import_failure/entities/import_failure.dart';

class ImportFailureService {
  // 接続先はテストで差し替えられるよう引数でも受け取る。省略すると起動時に渡した値を使う
  ImportFailureService({this.baseUrl = ApiConfig.baseUrl});

  final String baseUrl;

  /// 取り込めなかったメールを、失敗した日時の新しい順に返す。
  Future<List<ImportFailure>> getImportFailures() async {
    final response = await ApiHttp.get(Uri.parse('$baseUrl/import-failures'));

    if (response.statusCode != 200) {
      throw Exception('取り込めなかったメールの取得に失敗しました');
    }

    final items = jsonDecode(response.body) as List<dynamic>;

    return items
        .map((item) => ImportFailure.fromJson(item as Map<String, dynamic>))
        .toList();
  }
}
