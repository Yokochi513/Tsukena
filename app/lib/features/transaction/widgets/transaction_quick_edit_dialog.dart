import 'package:flutter/material.dart';
import 'package:tsukena/components/date_picker/date_picker.dart';
import 'package:tsukena/features/transaction/entities/transaction.dart';
import 'package:tsukena/features/transaction/entities/transaction_update.dart';
import 'package:tsukena/features/transaction/repositories/transaction_repository.dart';

/// 支出の支払日とメモだけを直すダイアログ。保存したら、直した後の支出を返して閉じる。
///
/// 変えた項目だけを送るので、カテゴリや確認待ちかどうかは変わらない。
/// 金額・店名・カテゴリなども直すときは、支出の一覧の修正ダイアログを使う
class TransactionQuickEditDialog extends StatefulWidget {
  const TransactionQuickEditDialog({super.key, required this.transaction});

  final Transaction transaction;

  @override
  State<TransactionQuickEditDialog> createState() =>
      _TransactionQuickEditDialogState();
}

class _TransactionQuickEditDialogState
    extends State<TransactionQuickEditDialog> {
  late final _memoController = TextEditingController(
    text: widget.transaction.memo,
  );
  late DateTime _paidDate = widget.transaction.paidDate;
  bool _saving = false;
  String? _error;

  @override
  void dispose() {
    _memoController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final transaction = widget.transaction;

    return AlertDialog(
      title: Text(
        transaction.merchant.isEmpty ? '(店名無し)' : transaction.merchant,
      ),
      content: SizedBox(
        width: 400,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            DatePickerField(
              label: '支払日',
              value: _paidDate,
              onChanged: (date) => setState(() => _paidDate = date),
            ),
            const SizedBox(height: 4),
            Text(
              '利用日 ${_formatDate(transaction.occurredDate)}。支払日を変えると、数える月も変わります',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _memoController,
              enabled: !_saving,
              decoration: const InputDecoration(
                labelText: 'メモ',
                hintText: '買った物など',
                border: OutlineInputBorder(),
              ),
              // Enter で改行する。保存はボタンで行う
              keyboardType: TextInputType.multiline,
              minLines: 3,
              maxLines: 6,
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
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('キャンセル'),
            ),
          ],
        ),
      ],
    );
  }

  Future<void> _save() async {
    final original = widget.transaction;
    // サーバーでも弾かれる（400）が、送る前に理由を出す
    if (_paidDate.isBefore(original.occurredDate)) {
      _showError('支払日は利用日以降にしてください');
      return;
    }

    // 前後の空白と空行は落とし、途中の改行は残す
    final memo = _memoController.text.trim();
    final paidDateChanged = !DateUtils.isSameDay(_paidDate, original.paidDate);
    final memoChanged = memo != original.memo;
    if (!paidDateChanged && !memoChanged) {
      Navigator.of(context).pop();
      return;
    }

    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      final updated = await TransactionService().patchTransaction(
        original.id,
        TransactionUpdate(
          paidDate: paidDateChanged ? _paidDate : null,
          memo: memoChanged ? memo : null,
        ),
      );
      if (!mounted) return;
      Navigator.of(context).pop(updated);
    } catch (_) {
      _showError('保存に失敗しました');
    }
  }

  void _showError(String message) {
    if (!mounted) return;
    setState(() {
      _saving = false;
      _error = message;
    });
  }

  String _formatDate(DateTime date) => '${date.year}/${date.month}/${date.day}';
}
