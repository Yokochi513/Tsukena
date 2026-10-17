import 'package:flutter/material.dart';
import 'package:tsukena/components/date_picker.dart';
import 'package:tsukena/features/transaction/entities/category.dart';
import 'package:tsukena/features/transaction/entities/transaction.dart';
import 'package:tsukena/features/transaction/entities/transaction_update.dart';
import 'package:tsukena/features/transaction/repositories/transaction_repository.dart';

class TransactionEditDialog extends StatefulWidget {
  const TransactionEditDialog({
    super.key,
    required this.transaction,
    required this.categories,
  });

  final Transaction transaction;
  final Map<int, Category> categories;

  @override
  State<TransactionEditDialog> createState() => _TransactionEditDialogState();
}

class _TransactionEditDialogState extends State<TransactionEditDialog> {
  late DateTime _occurredDate;
  late DateTime _paidDate;
  late String _amountText;
  late String _merchant;
  int? _categoryId;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    final transaction = widget.transaction;
    _occurredDate = transaction.occurredDate;
    _paidDate = transaction.paidDate;
    _amountText = transaction.amount.toString();
    _merchant = transaction.merchant;
    _categoryId = transaction.categoryId;
  }

  @override
  Widget build(BuildContext context) {
    final transaction = widget.transaction;
    final categories = widget.categories.values.toList()
      ..sort((a, b) {
        final order = a.sortOrder.compareTo(b.sortOrder);
        return order != 0 ? order : a.id.compareTo(b.id);
      });

    return AlertDialog(
      title: const Text('取引を編集'),
      content: SizedBox(
        width: 400,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              DatePickerField(
                label: '利用日',
                value: _occurredDate,
                onChanged: (date) => setState(() => _occurredDate = date),
              ),
              const SizedBox(height: 16),
              DatePickerField(
                label: '支払日',
                value: _paidDate,
                onChanged: (date) => setState(() => _paidDate = date),
              ),
              const SizedBox(height: 16),
              TextFormField(
                decoration: const InputDecoration(labelText: '金額'),
                keyboardType: TextInputType.number,
                initialValue: _amountText,
                onChanged: (value) => _amountText = value,
              ),
              const SizedBox(height: 16),
              TextFormField(
                decoration: const InputDecoration(labelText: '店名'),
                initialValue: _merchant,
                onChanged: (value) => _merchant = value,
              ),
              const SizedBox(height: 16),
              DropdownButtonFormField<int>(
                decoration: const InputDecoration(labelText: 'カテゴリ'),
                // 確認待ちの取引は未選択から始める。未設定に戻す選択肢は無い（サーバーが受け付けないため）
                initialValue: widget.categories.containsKey(_categoryId)
                    ? _categoryId
                    : null,
                hint: const Text('未分類'),
                items: [
                  for (final category in categories)
                    DropdownMenuItem(
                      value: category.id,
                      child: Text('${category.emoji} ${category.name}'),
                    ),
                ],
                onChanged: (value) => setState(() => _categoryId = value),
              ),
              const SizedBox(height: 16),
              // 修正できない項目は参考として表示だけする
              Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  '支払い手段: ${transaction.paymentMethod}',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
            ],
          ),
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
            TextButton(
              onPressed: () => _delete(transaction),
              style: TextButton.styleFrom(
                foregroundColor: Theme.of(context).colorScheme.error,
              ),
              child: const Text('削除'),
            ),
          ],
        ),
      ],
    );
  }

  Future<void> _save() async {
    final amount = int.tryParse(_amountText);
    if (amount == null || amount < 1) {
      _showError('金額は1円以上の整数で入力してください');
      return;
    }
    if (_paidDate.isBefore(_occurredDate)) {
      _showError('支払日は利用日以降にしてください');
      return;
    }

    // 変えた項目だけを送る。送った項目に応じてサーバーの処理が変わるため
    // （利用日だけなら支払日の計算し直し、カテゴリなら確定とルールの学習）
    final original = widget.transaction;
    final update = TransactionUpdate(
      occurredDate: DateUtils.isSameDay(_occurredDate, original.occurredDate)
          ? null
          : _occurredDate,
      paidDate: DateUtils.isSameDay(_paidDate, original.paidDate)
          ? null
          : _paidDate,
      amount: amount == original.amount ? null : amount,
      merchant: _merchant == original.merchant ? null : _merchant,
      categoryId: _categoryId == original.categoryId ? null : _categoryId,
    );

    setState(() => _saving = true);
    try {
      await TransactionService(
        baseUrl: 'http://127.0.0.1:8000',
      ).patchTransaction(original.id, update);
    } catch (_) {
      if (!mounted) return;
      setState(() => _saving = false);
      _showError('取引の修正に失敗しました');
      return;
    }
    if (!mounted) return;
    Navigator.of(context).pop(true);
  }

  void _showError(String message) {
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _delete(Transaction transaction) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('この取引を削除しますか?'),
        actions: [
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              TextButton(
                onPressed: () => Navigator.of(context).pop(true),
                style: TextButton.styleFrom(
                  foregroundColor: Theme.of(context).colorScheme.error,
                ),
                child: const Text('削除'),
              ),
              TextButton(
                onPressed: () => Navigator.of(context).pop(false),
                child: const Text('キャンセル'),
              ),
            ],
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    await TransactionService(
      baseUrl: 'http://127.0.0.1:8000',
    ).deleteTransaction(transaction.id);
    if (!mounted) return;
    Navigator.of(context).pop(true);
  }
}
