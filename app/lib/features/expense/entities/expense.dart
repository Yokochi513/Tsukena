import 'package:flutter/material.dart';

class Expense {
  int? id;
  DateTime occurredDate;
  TimeOfDay? occurredTime;
  String merchant;
  String paymentMethod;
  double amount;

  Expense({
    this.id,
    DateTime? occurredDate,
    this.occurredTime,
    this.merchant = '',
    this.paymentMethod = '',
    this.amount = 0.0,
  }) : occurredDate = occurredDate ?? DateTime.now();

  factory Expense.fromJson(Map<String, dynamic> json) {
    return Expense(
      id: json['id'] as int?,
      occurredDate: DateTime.parse(json['occurred_date'] as String),
      occurredTime: json['occurred_time'] != null
          ? TimeOfDay(
              hour: int.parse((json['occurred_time'] as String).split(':')[0]),
              minute: int.parse(
                (json['occurred_time'] as String).split(':')[1],
              ),
            )
          : null,
      merchant: json['merchant'] as String,
      paymentMethod: json['payment_method'] as String,
      amount: (json['amount'] as num).toDouble(),
    );
  }
}
