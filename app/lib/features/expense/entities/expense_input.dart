import 'package:flutter/material.dart';

class ExpenseInput {
  DateTime occurredDate = DateTime.now();
  TimeOfDay? occurredTime;
  String merchant = '';
  String paymentMethod = '';
  double amount = 0.0;
}
