import 'dart:convert';

import 'package:tsukena/core/api_config.dart';
import 'package:tsukena/core/api_http.dart';
import 'package:tsukena/features/budget/entities/budget.dart';

/// 予算が1円以上の整数でない（422）。
class InvalidBudgetException implements Exception {}

class BudgetService {
  // 接続先はテストで差し替えられるよう引数でも受け取る。省略すると起動時に渡した値を使う
  BudgetService({this.baseUrl = ApiConfig.baseUrl});

  final String baseUrl;

  Future<Budget> getBudget() async {
    final response = await ApiHttp.get(Uri.parse('$baseUrl/budget'));

    if (response.statusCode != 200) {
      throw Exception('予算の取得に失敗しました');
    }

    return Budget.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
  }

  Future<Budget> putBudget(Budget budget) async {
    final response = await ApiHttp.put(
      Uri.parse('$baseUrl/budget'),
      body: jsonEncode(budget.toJson()),
    );

    if (response.statusCode == 422) {
      throw InvalidBudgetException();
    }
    if (response.statusCode != 200) {
      throw Exception('予算の変更に失敗しました');
    }

    return Budget.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
  }
}
