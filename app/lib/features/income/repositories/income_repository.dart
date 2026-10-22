import 'dart:convert';

import 'package:tsukena/features/income/entities/income.dart';
import 'package:tsukena/core/api_config.dart';
import 'package:tsukena/core/api_http.dart';
import 'package:tsukena/features/income/entities/income_input.dart';

class IncomeService {
  // 接続先はテストで差し替えられるよう引数でも受け取る。省略すると起動時に渡した値を使う
  IncomeService({this.baseUrl = ApiConfig.baseUrl});

  final String baseUrl;

  // month は入金日の月（"YYYY-MM"）。省略できない（→ docs/api_list.md 2.3）
  Future<List<Income>> getIncomes(String month) async {
    final response = await ApiHttp.get(
      Uri.parse('$baseUrl/incomes').replace(queryParameters: {'month': month}),
    );

    if (response.statusCode != 200) {
      throw Exception('収入の取得に失敗しました');
    }

    final items = jsonDecode(response.body) as List<dynamic>;

    return items
        .map((item) => Income.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<Income> postIncome(IncomeInput incomeInput) async {
    final response = await ApiHttp.post(
      Uri.parse('$baseUrl/incomes'),
      body: jsonEncode(incomeInput.toJson()),
    );

    if (response.statusCode != 201) {
      throw Exception('収入の登録に失敗しました');
    }

    return Income.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
  }

  Future<Income> patchIncome(int incomeId, IncomeInput incomeInput) async {
    final response = await ApiHttp.patch(
      Uri.parse('$baseUrl/incomes/$incomeId'),
      body: jsonEncode(incomeInput.toJson()),
    );

    if (response.statusCode != 200) {
      throw Exception('収入の修正に失敗しました');
    }

    return Income.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
  }

  Future<void> deleteIncome(int incomeId) async {
    final response = await ApiHttp.delete(
      Uri.parse('$baseUrl/incomes/$incomeId'),
    );

    if (response.statusCode != 204) {
      throw Exception('収入の削除に失敗しました');
    }
  }
}
