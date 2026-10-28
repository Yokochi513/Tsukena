import 'package:flutter/material.dart';
import 'package:tsukena/features/transaction/entities/charge.dart';

enum TransactionStatus {
  confirmed,
  pending;

  static TransactionStatus fromJson(String value) =>
      TransactionStatus.values.byName(value);
}

enum TransactionSource {
  gmail,
  discord;

  static TransactionSource fromJson(String value) =>
      TransactionSource.values.byName(value);
}

class Transaction {
  int id;
  DateTime occurredDate;
  TimeOfDay? occurredTime;
  DateTime paidDate;
  int amount;
  String merchant;
  String memo;
  int? categoryId;
  TransactionStatus status;
  String paymentMethod;
  TransactionSource source;
  DateTime createdAt;
  DateTime updatedAt;
  PaymentPlan paymentPlan;

  /// スキップ払いなら繰り延べる月数、分割払いなら回数。ほかは null
  int? planCount;

  /// 引き落としの予定。1回払い以外では、paidDate は1回払いだったときの支払日になる
  List<Charge> charges;

  Transaction({
    required this.id,
    required this.occurredDate,
    this.occurredTime,
    required this.paidDate,
    required this.amount,
    this.merchant = '',
    this.memo = '',
    this.categoryId,
    required this.status,
    required this.paymentMethod,
    required this.source,
    required this.createdAt,
    required this.updatedAt,
    this.paymentPlan = PaymentPlan.lump,
    this.planCount,
    this.charges = const [],
  });

  factory Transaction.fromJson(Map<String, dynamic> json) {
    return Transaction(
      id: json['id'] as int,
      occurredDate: DateTime.parse(json['occurred_date'] as String),
      occurredTime: _parseTime(json['occurred_time'] as String?),
      paidDate: DateTime.parse(json['paid_date'] as String),
      amount: json['amount'] as int,
      merchant: json['merchant'] as String,
      memo: json['memo'] as String,
      categoryId: json['category_id'] as int?,
      status: TransactionStatus.fromJson(json['status'] as String),
      paymentMethod: json['payment_method'] as String,
      source: TransactionSource.fromJson(json['source'] as String),
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
      paymentPlan: PaymentPlan.fromJson(json['payment_plan'] as String),
      planCount: json['plan_count'] as int?,
      charges: (json['charges'] as List<dynamic>)
          .map((c) => Charge.fromJson(c as Map<String, dynamic>))
          .toList(),
    );
  }

  /// month（月の初日）に引き落とされる回。月の集計は、1回払いなら支払日、ほかはこの回で数える
  List<Charge> chargesIn(DateTime month) => charges
      .where(
        (c) => c.paidDate.year == month.year && c.paidDate.month == month.month,
      )
      .toList();

  /// month に引き落とされる額（手数料を含む）
  int amountIn(DateTime month) =>
      chargesIn(month).fold(0, (sum, c) => sum + c.amount);

  /// 支払い方法と、month の引き落としが何回目か（「分割払い 2/10回」など）。1回払いなら null
  String? planLabelIn(DateTime? month) {
    switch (paymentPlan) {
      case PaymentPlan.lump:
        return null;
      case PaymentPlan.skip:
        return '${paymentPlan.label}（$planCountか月後）';
      case PaymentPlan.installment:
        final charge = month == null ? null : chargesIn(month).firstOrNull;
        return charge == null
            ? '${paymentPlan.label} $planCount回'
            : '${paymentPlan.label} ${charge.seq}/$planCount回';
      case PaymentPlan.revolving:
        return paymentPlan.label;
    }
  }

  // サーバーは時刻を "HH:MM" で返す。分からなければ null
  static TimeOfDay? _parseTime(String? value) {
    if (value == null) return null;
    final parts = value.split(':');
    return TimeOfDay(hour: int.parse(parts[0]), minute: int.parse(parts[1]));
  }
}
