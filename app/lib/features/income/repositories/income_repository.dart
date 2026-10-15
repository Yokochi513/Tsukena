import 'dart:convert';

import 'package:tsukena/features/income/entities/income.dart';
import 'package:http/http.dart' as http;

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
}
