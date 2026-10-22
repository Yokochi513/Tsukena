import 'dart:convert';

import 'package:tsukena/core/api_config.dart';
import 'package:tsukena/core/api_http.dart';
import 'package:tsukena/features/month_summary/entities/monthly_summary.dart';

class MonthSummaryService {
  // 接続先はテストで差し替えられるよう引数でも受け取る。省略すると起動時に渡した値を使う
  MonthSummaryService({this.baseUrl = ApiConfig.baseUrl});

  final String baseUrl;

  // month は "YYYY-MM"。記録の無い月や来月以降の月でも、合計を0にして返ってくる
  Future<MonthlySummary> getMonthlySummary(String month) async {
    final response = await ApiHttp.get(
      Uri.parse('$baseUrl/months/$month/summary'),
    );

    if (response.statusCode != 200) {
      throw Exception('月の集計の取得に失敗しました');
    }

    return MonthlySummary.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }
}
