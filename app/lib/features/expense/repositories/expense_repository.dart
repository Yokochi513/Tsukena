import 'dart:convert';

import 'package:tsukena/features/expense/entities/expense.dart';
import 'package:http/http.dart' as http;

class ExpenseService {
  ExpenseService({required this.baseUrl});

  final String baseUrl;

  Future<List<Expense>> getExpenses() async {
    final response = await http.get(Uri.parse('$baseUrl/expenses'));

    if (response.statusCode != 200) {
      throw Exception('支出の取得に失敗しました');
    }

    final items = jsonDecode(response.body) as List<dynamic>;

    return items
        .map((item) => Expense.fromJson(item as Map<String, dynamic>))
        .toList();
  }
}
