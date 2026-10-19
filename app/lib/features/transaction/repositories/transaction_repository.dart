import 'dart:convert';

import 'package:tsukena/core/api_config.dart';
import 'package:tsukena/core/api_http.dart';
import 'package:tsukena/features/transaction/entities/transaction.dart';
import 'package:tsukena/features/transaction/entities/transaction_update.dart';

class TransactionService {
  // 接続先はテストで差し替えられるよう引数でも受け取る。省略すると起動時に渡した値を使う
  TransactionService({this.baseUrl = ApiConfig.baseUrl});

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
    final response = await ApiHttp.get(uri);

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
    final response = await ApiHttp.patch(
      Uri.parse('$baseUrl/transactions/$transactionId'),
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
    final response = await ApiHttp.delete(
      Uri.parse('$baseUrl/transactions/$transactionId'),
    );

    if (response.statusCode != 204) {
      throw Exception('取引の削除に失敗しました');
    }
  }
}
