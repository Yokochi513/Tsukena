import 'package:flutter/material.dart';
import 'package:tsukena/components/date_picker.dart';
import 'package:tsukena/features/income/entities/income_input.dart';

class IncomeEditPage extends StatefulWidget {
  const IncomeEditPage({super.key});

  @override
  State<IncomeEditPage> createState() => _IncomeEditPageState();
}

class _IncomeEditPageState extends State<IncomeEditPage> {
  final fieldInput = IncomeInput();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            DatePickerField(
              label: "入金日",
              value: fieldInput.receivedDate,
              onChanged: (date) {
                setState(() {
                  fieldInput.receivedDate = date;
                });
              },
            ),
            const SizedBox(height: 16),
            TextField(
              decoration: const InputDecoration(labelText: '金額'),
              keyboardType: TextInputType.number,
              onChanged: (value) {
                fieldInput.amount = int.tryParse(value) ?? 0;
              },
            ),
            const SizedBox(height: 16),
            TextField(
              decoration: const InputDecoration(labelText: 'メモ'),
              keyboardType: TextInputType.text,
              onChanged: (value) {
                fieldInput.memo = value;
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
