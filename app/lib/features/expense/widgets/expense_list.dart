import 'package:flutter/material.dart';
import 'package:tsukena/features/expense/entities/expense.dart';

class ExpenseList extends StatelessWidget {
  const ExpenseList({super.key, required this.expenses});

  final List<Expense> expenses;

  @override
  Widget build(BuildContext context) {
    if (expenses.isEmpty) {
      return const Center(child: Text('支出がありません'));
    }

    return ListView.builder(
      itemCount: expenses.length,
      itemBuilder: (context, index) {
        final expense = expenses[index];

        return ListTile(
          title: Text(expense.merchant),
          subtitle: Text(expense.paymentMethod),
          trailing: Text('${expense.amount}円'),
        );
      },
    );
  }
}
