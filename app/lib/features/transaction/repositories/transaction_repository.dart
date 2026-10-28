import 'dart:convert';

import 'package:tsukena/core/api_config.dart';
import 'package:tsukena/core/api_http.dart';
import 'package:tsukena/features/transaction/entities/charge.dart';
import 'package:tsukena/features/transaction/entities/transaction.dart';
import 'package:tsukena/features/transaction/entities/transaction_update.dart';

class TransactionService {
  // 接続先はテストで差し替えられるよう引数でも受け取る。省略すると起動時に渡した値を使う
  TransactionService({this.baseUrl = ApiConfig.baseUrl});

  final String baseUrl;

  // month は支払日の月（"YYYY-MM"）、q は店名かメモに含む文字（表記の揺れはサーバーが吸収する）。
  // すべて省略すると全件を返す
  Future<List<Transaction>> getTransactions({
    String? month,
    TransactionStatus? status,
    String? q,
  }) async {
    final query = {'month': ?month, 'status': ?status?.name, 'q': ?q};
    final uri = Uri.parse('$baseUrl/transactions').replace(
      // 空の Map を渡すと末尾に "?" だけが付くため、絞り込みが無いときは null にする
      queryParameters: query.isEmpty ? null : query,
    );
    final response = await ApiHttp.get(uri);

    if (response.statusCode != 200) {
      throw Exception('支出の取得に失敗しました');
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
      throw Exception('支出の修正に失敗しました');
    }

    return Transaction.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }

  /// 支払い方法を変える。count はスキップ払いなら繰り延べる月数、分割払いなら回数。
  /// その支払い手段では変えられないとき（現金や、設定に手数料率の無いカード）は PaymentPlanNotAvailable を投げる
  Future<Transaction> putPaymentPlan(
    int transactionId,
    PaymentPlan plan, {
    int? count,
  }) async {
    final response = await ApiHttp.put(
      Uri.parse('$baseUrl/transactions/$transactionId/payment-plan'),
      body: jsonEncode({'plan': plan.name, 'count': ?count}),
    );

    if (response.statusCode == 422) throw PaymentPlanNotAvailable();
    if (response.statusCode != 200) {
      throw Exception('支払い方法の変更に失敗しました');
    }

    return Transaction.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }

  /// スキップ・分割払いの1回分の手数料を直す。fee が null なら計算した額に戻す
  Future<Transaction> putChargeFee(int transactionId, int seq, int? fee) async {
    final response = await ApiHttp.put(
      Uri.parse('$baseUrl/transactions/$transactionId/charges/$seq/fee'),
      body: jsonEncode({'fee': fee}),
    );

    if (response.statusCode != 200) {
      throw Exception('手数料の修正に失敗しました');
    }

    return Transaction.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }

  /// 支払い手段のリボ払いの、月ごとの引き落とし（リボにした支出の全部を合わせた額）
  Future<List<RevolvingMonth>> getRevolving(String paymentMethod) async {
    final response = await ApiHttp.get(
      Uri.parse('$baseUrl/revolving/${Uri.encodeComponent(paymentMethod)}'),
    );

    if (response.statusCode != 200) {
      throw Exception('リボ払いの予定の取得に失敗しました');
    }

    return _revolvingMonths(response.body);
  }

  /// リボ払いのある月の手数料（リボ全体の額）を直す。fee が null なら計算した額に戻す
  Future<List<RevolvingMonth>> putRevolvingFee(
    String paymentMethod,
    String month,
    int? fee,
  ) async {
    final response = await ApiHttp.put(
      Uri.parse(
        '$baseUrl/revolving/${Uri.encodeComponent(paymentMethod)}/months/$month/fee',
      ),
      body: jsonEncode({'fee': fee}),
    );

    if (response.statusCode != 200) {
      throw Exception('手数料の修正に失敗しました');
    }

    return _revolvingMonths(response.body);
  }

  List<RevolvingMonth> _revolvingMonths(String body) {
    final items = jsonDecode(body) as List<dynamic>;
    return items
        .map((item) => RevolvingMonth.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<void> deleteTransaction(int transactionId) async {
    final response = await ApiHttp.delete(
      Uri.parse('$baseUrl/transactions/$transactionId'),
    );

    if (response.statusCode != 204) {
      throw Exception('支出の削除に失敗しました');
    }
  }
}

/// その支払い手段では、支払い方法を変えられない
class PaymentPlanNotAvailable implements Exception {}
