import 'package:flutter/material.dart';

class ParsedPayment {
  ParsedPayment({
    required this.occurredDate,
    this.occurredTime,
    required this.amount,
    required this.merchant,
    required this.paymentMethod,
  });

  final DateTime occurredDate;
  final TimeOfDay? occurredTime;
  final double amount;
  final String merchant;
  final String paymentMethod;
}
