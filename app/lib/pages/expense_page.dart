import 'package:flutter/material.dart';
import 'package:tsukena/features/expense/entities/expense_input.dart';

class ExpensePage extends StatefulWidget {
  const ExpensePage({super.key});

  @override
  State<ExpensePage> createState() => _ExpensePageState();
}

class _ExpensePageState extends State<ExpensePage> {
  final fieldInput = ExpenseInput();

  @override
  void initState() {
    super.initState();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('支出登録')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            TextField(
              decoration: InputDecoration(labelText: '日付'),
              keyboardType: TextInputType.datetime,
              onChanged: (value) {
                fieldInput.occurredDate =
                    DateTime.tryParse(value) ?? DateTime.now();
              },
            ),
            const SizedBox(height: 16),
            TextField(
              decoration: const InputDecoration(labelText: '店名'),
              keyboardType: TextInputType.text,
              onChanged: (value) {
                fieldInput.merchant = value;
              },
            ),
            const SizedBox(height: 16),
            TextField(
              decoration: const InputDecoration(labelText: '支払方法'),
              keyboardType: TextInputType.text,
              onChanged: (value) {
                fieldInput.paymentMethod = value;
              },
            ),
            const SizedBox(height: 16),
            TextField(
              decoration: const InputDecoration(labelText: '金額'),
              keyboardType: TextInputType.number,
              onChanged: (value) {
                fieldInput.amount = double.tryParse(value) ?? 0.0;
              },
            ),
            const SizedBox(height: 16),
            ElevatedButton(onPressed: () {}, child: const Text('保存')),
          ],
        ),
      ),
    );
  }
}
