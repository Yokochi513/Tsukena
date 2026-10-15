import 'package:flutter/material.dart';
import 'package:tsukena/components/date_picker.dart';
import 'package:tsukena/features/income/entities/income.dart';
import 'package:tsukena/features/income/entities/income_input.dart';
import 'package:tsukena/features/income/repositories/income_repository.dart';

class IncomeEditDialog extends StatefulWidget {
  const IncomeEditDialog({super.key, this.income});

  final Income? income;

  @override
  State<IncomeEditDialog> createState() => _IncomeEditDialogState();
}

class _IncomeEditDialogState extends State<IncomeEditDialog> {
  final fieldInput = IncomeInput();

  bool get _isEdit => widget.income != null;

  @override
  void initState() {
    super.initState();
    final income = widget.income;
    if (income != null) {
      fieldInput.receivedDate = income.receivedDate;
      fieldInput.amount = income.amount;
      fieldInput.memo = income.memo;
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(_isEdit ? '収入を編集' : '収入を追加'),
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
            TextFormField(
              decoration: const InputDecoration(labelText: '金額'),
              keyboardType: TextInputType.number,
              initialValue: fieldInput.amount != 0
                  ? fieldInput.amount.toString()
                  : "",
              onChanged: (value) {
                fieldInput.amount = int.tryParse(value) ?? 0;
              },
            ),
            const SizedBox(height: 16),
            TextFormField(
              decoration: const InputDecoration(labelText: 'メモ'),
              keyboardType: TextInputType.text,
              initialValue: fieldInput.memo,
              onChanged: (value) {
                fieldInput.memo = value;
              },
            ),
          ],
        ),
      ),
      actions: [
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            TextButton(onPressed: _save, child: const Text('保存')),
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('キャンセル'),
            ),
          ],
        ),
      ],
    );
  }

  Future<void> _save() async {
    final service = IncomeService(baseUrl: 'http://127.0.0.1:8000');
    final income = widget.income;
    if (_isEdit) {
      await service.patchIncome(income!.id, fieldInput);
    } else {
      await service.postIncome(fieldInput);
    }
    if (!mounted) return;
    Navigator.of(context).pop(true);
  }
}
