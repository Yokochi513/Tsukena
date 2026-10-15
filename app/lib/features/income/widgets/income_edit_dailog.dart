import 'package:flutter/material.dart';
import 'package:tsukena/components/date_picker.dart';
import 'package:tsukena/features/income/entities/income_input.dart';
import 'package:tsukena/features/income/repositories/income_repository.dart';

class IncomeEditDialog extends StatefulWidget {
  const IncomeEditDialog({super.key});

  @override
  State<IncomeEditDialog> createState() => _IncomeEditDialogState();
}

class _IncomeEditDialogState extends State<IncomeEditDialog> {
  final fieldInput = IncomeInput();

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('収入を追加'),
      content: SizedBox(
        width: 400,
        child: Column(
          mainAxisSize: MainAxisSize.min,
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
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(false),
          child: const Text('キャンセル'),
        ),
        ElevatedButton(
          onPressed: () async {
            await IncomeService(
              baseUrl: 'http://127.0.0.1:8000',
            ).postIncome(fieldInput);
            if (!context.mounted) return;
            Navigator.of(context).pop(true);
          },
          child: const Text('保存'),
        ),
      ],
    );
  }
}
