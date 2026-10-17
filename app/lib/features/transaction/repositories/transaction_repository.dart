import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:tsukena/features/transaction/entities/transaction.dart';
import 'package:tsukena/features/transaction/entities/transaction_update.dart';

class TransactionService {
  TransactionService({required this.baseUrl});

  final String baseUrl;

  // month は支払日の月（"YYYY-MM"）。どちらも省略すると全件を返す
  Future<List<Transaction>> getTransactions({
    String? month,
    TransactionStatus? status,
  }) async {
    final query = {'month': ?month, 'status': ?status?.name};
    final uri = Uri.parse('$baseUrl/transactions').replace(
      // 空の Map を渡すと末尾に "?" だけが付くため、絞り込みが無いときは null にする
      queryParameters: query.isEmpty ? null : query,
    );
    final response = await http.get(uri);

    if (response.statusCode != 200) {
      throw Exception('取引の取得に失敗しました');
    }

    final items = jsonDecode(response.body) as List<dynamic>;

    return items
        .map((item) => Transaction.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<Transaction> patchTransaction(
    int transactionId,
    TransactionUpdate transactionUpdate,
  ) async {
    final response = await http.patch(
      Uri.parse('$baseUrl/transactions/$transactionId'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(transactionUpdate.toJson()),
    );

    if (response.statusCode != 200) {
      throw Exception('取引の修正に失敗しました');
    }

    return Transaction.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }

  Future<void> deleteTransaction(int transactionId) async {
    final response = await http.delete(
      Uri.parse('$baseUrl/transactions/$transactionId'),
    );

    if (response.statusCode != 204) {
      throw Exception('収入の削除に失敗しました');
    }
  }
}
