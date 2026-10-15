import 'package:flutter/material.dart';

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
  int? categoryId;
  TransactionStatus status;
  String paymentMethod;
  TransactionSource source;
  DateTime createdAt;
  DateTime updatedAt;

  Transaction({
    required this.id,
    required this.occurredDate,
    this.occurredTime,
    required this.paidDate,
    required this.amount,
    this.merchant = '',
    this.categoryId,
    required this.status,
    required this.paymentMethod,
    required this.source,
    required this.createdAt,
    required this.updatedAt,
  });

  factory Transaction.fromJson(Map<String, dynamic> json) {
    return Transaction(
      id: json['id'] as int,
      occurredDate: DateTime.parse(json['occurred_date'] as String),
      occurredTime: _parseTime(json['occurred_time'] as String?),
      paidDate: DateTime.parse(json['paid_date'] as String),
      amount: json['amount'] as int,
      merchant: json['merchant'] as String,
      categoryId: json['category_id'] as int?,
      status: TransactionStatus.fromJson(json['status'] as String),
      paymentMethod: json['payment_method'] as String,
      source: TransactionSource.fromJson(json['source'] as String),
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
    );
  }

  // サーバーは時刻を "HH:MM" で返す。分からなければ null
  static TimeOfDay? _parseTime(String? value) {
    if (value == null) return null;
    final parts = value.split(':');
    return TimeOfDay(hour: int.parse(parts[0]), minute: int.parse(parts[1]));
  }
}
