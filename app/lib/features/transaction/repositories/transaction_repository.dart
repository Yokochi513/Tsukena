import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:tsukena/features/transaction/entities/transaction.dart';

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
}
