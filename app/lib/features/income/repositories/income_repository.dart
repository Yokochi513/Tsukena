import 'dart:convert';

import 'package:tsukena/features/income/entities/income.dart';
import 'package:http/http.dart' as http;
import 'package:tsukena/features/income/entities/income_input.dart';

class IncomeService {
  IncomeService({required this.baseUrl});

  final String baseUrl;

  Future<List<Income>> getIncomes() async {
    final response = await http.get(Uri.parse('$baseUrl/incomes'));

    if (response.statusCode != 200) {
      throw Exception('収入の取得に失敗しました');
    }

    final items = jsonDecode(response.body) as List<dynamic>;

    return items
        .map((item) => Income.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<Income> postIncome(IncomeInput incomeInput) async {
    final response = await http.post(
      Uri.parse('$baseUrl/incomes'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(incomeInput.toJson()),
    );

    if (response.statusCode != 201) {
      throw Exception('収入の登録に失敗しました');
    }

    return Income.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
  }

  Future<Income> patchIncome(int incomeId, IncomeInput incomeInput) async {
    final response = await http.patch(
      Uri.parse('$baseUrl/incomes/$incomeId'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(incomeInput.toJson()),
    );

    if (response.statusCode != 200) {
      throw Exception('収入の修正に失敗しました');
    }

    return Income.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
  }
}
