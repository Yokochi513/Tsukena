import 'package:flutter/material.dart';
import 'package:tsukena/features/budget/entities/budget.dart';
import 'package:tsukena/features/budget/repositories/budget_repository.dart';

/// 月の予算を変えるダイアログ。変えたら true を返して閉じる。
///
/// 予算は月ごとに持たないため、変えると過去の月の残りもこの値で計算し直される。そのことを先に伝える
class BudgetEditDialog extends StatefulWidget {
  const BudgetEditDialog({super.key, required this.budget});

  final Budget budget;

  @override
  State<BudgetEditDialog> createState() => _BudgetEditDialogState();
}

class _BudgetEditDialogState extends State<BudgetEditDialog> {
  late String _amountText;
  bool _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _amountText = widget.budget.monthlyBudget.toString();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('月の予算を変更'),
      content: SizedBox(
        width: 400,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextFormField(
              decoration: const InputDecoration(
                labelText: '月の予算',
                suffixText: '円',
              ),
              keyboardType: TextInputType.number,
              autofocus: true,
              initialValue: _amountText,
              onChanged: (value) => _amountText = value,
            ),
            const SizedBox(height: 16),
            Text(
              '予算は月ごとには持ちません。変えると、過去の月の残りもこの金額で計算し直されます',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            if (_error case final error?) ...[
              const SizedBox(height: 8),
              Text(
                error,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ],
          ],
        ),
      ),
      actions: [
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            TextButton(
              onPressed: _saving ? null : _save,
              child: const Text('保存'),
            ),
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
    final amount = int.tryParse(_amountText.trim());
    if (amount == null || amount < 1) {
      _showError('予算は1円以上の整数で入力してください');
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await BudgetService().putBudget(Budget(monthlyBudget: amount));
    } on InvalidBudgetException {
      _showError('予算は1円以上の整数で入力してください');
      return;
    } catch (_) {
      _showError('予算の変更に失敗しました');
      return;
    }
    if (!mounted) return;
    Navigator.of(context).pop(true);
  }

  void _showError(String message) {
    if (!mounted) return;
    setState(() {
      _saving = false;
      _error = message;
    });
  }
}
