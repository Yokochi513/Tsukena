import 'package:flutter/material.dart';
import 'package:tsukena/features/transaction/entities/category.dart';
import 'package:tsukena/features/transaction/entities/transaction.dart';
import 'package:tsukena/features/transaction/entities/transaction_update.dart';
import 'package:tsukena/features/transaction/repositories/transaction_repository.dart';

class TransactionPendingSheet extends StatefulWidget {
  const TransactionPendingSheet({
    super.key,
    required this.transactions,
    required this.categories,
  });

  final List<Transaction> transactions;
  final Map<int, Category> categories;

  @override
  State<TransactionPendingSheet> createState() =>
      _TransactionPendingSheetState();
}

class _TransactionPendingSheetState extends State<TransactionPendingSheet> {
  final Map<int, int> _confirmed = {};
  final Set<int> _saving = {};
  final Map<int, TextEditingController> _memoControllers = {};
  // サーバーに保存済みのメモ。入力欄と比べて、変わったときだけ送る
  final Map<int, String> _savedMemos = {};
  String? _error;

  @override
  void initState() {
    super.initState();
    for (final transaction in widget.transactions) {
      _memoControllers[transaction.id] = TextEditingController(
        text: transaction.memo,
      );
      _savedMemos[transaction.id] = transaction.memo;
    }
  }

  @override
  void dispose() {
    for (final controller in _memoControllers.values) {
      controller.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final categories = widget.categories.values.toList()
      ..sort((a, b) {
        final order = a.sortOrder.compareTo(b.sortOrder);
        return order != 0 ? order : a.id.compareTo(b.id);
      });
    final remaining = widget.transactions.length - _confirmed.length;

    // 幕を押したとき・戻る操作・［閉じる］のどれで閉じても、書きかけのメモを保存してから閉じる
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) async {
        if (didPop) return;
        await _saveAllMemos();
        // 保存に失敗したら閉じずに残し、エラーを見せる
        if (context.mounted && _error == null) Navigator.pop(context);
      },
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(24, 16, 24, 8),
            child: Text(
              remaining == 0 ? 'すべて確認しました' : '確認待ち（残り $remaining件）',
              style: textTheme.titleLarge,
            ),
          ),
          // 件数が少なければ短く、多ければ showModalTopSheet の高さの上限で止まってスクロールする
          Flexible(
            child: ListView.separated(
              shrinkWrap: true,
              itemCount: widget.transactions.length,
              separatorBuilder: (context, index) => const Divider(height: 1),
              itemBuilder: (context, index) =>
                  _buildItem(widget.transactions[index], categories, textTheme),
            ),
          ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.fromLTRB(24, 8, 24, 0),
              child: Text(
                _error!,
                style: textTheme.bodySmall?.copyWith(
                  color: Theme.of(context).colorScheme.error,
                ),
              ),
            ),
          Padding(
            padding: const EdgeInsets.fromLTRB(24, 8, 24, 16),
            child: Align(
              alignment: Alignment.centerRight,
              child: TextButton(
                onPressed: () => Navigator.maybePop(context),
                child: const Text('閉じる'),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildItem(
    Transaction transaction,
    List<Category> categories,
    TextTheme textTheme,
  ) {
    final confirmedId = _confirmed[transaction.id];
    final saving = _saving.contains(transaction.id);

    final time = transaction.occurredTime;
    final date = _formatDate(transaction.occurredDate);
    final datetime = time == null ? date : '$date ${_formatTime(time)}';

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  transaction.merchant.isEmpty
                      ? '(店名無し)'
                      : transaction.merchant,
                  style: textTheme.titleMedium,
                ),
              ),
              Text(
                '¥${_formatAmount(transaction.amount)}',
                style: textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          Text(
            '$datetime ・ ${transaction.paymentMethod}',
            style: textTheme.bodySmall,
          ),
          // Discord で一言添えた現金の記録は、何を買ったかがメモに入っている。そのまま書き直せる
          TextField(
            controller: _memoControllers[transaction.id],
            enabled: !saving,
            decoration: const InputDecoration(
              labelText: 'メモ',
              hintText: '何を買ったか',
              isDense: true,
            ),
            textInputAction: TextInputAction.done,
            onSubmitted: (_) => _saveMemo(transaction),
          ),
          const SizedBox(height: 8),
          // カテゴリが多くても1行に収め、横にスクロールさせる
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                for (final category in categories)
                  Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: ChoiceChip(
                      label: Text('${category.emoji} ${category.name}'),
                      selected: confirmedId == category.id,
                      onSelected: saving
                          ? null
                          : (_) => _confirm(transaction, category),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _confirm(Transaction transaction, Category category) async {
    if (_confirmed[transaction.id] == category.id) return;
    setState(() {
      _saving.add(transaction.id);
      _error = null;
    });

    // 書きかけのメモがあれば、カテゴリと一緒に送る
    final memo = _memoControllers[transaction.id]!.text.trim();
    final memoChanged = memo != _savedMemos[transaction.id];

    try {
      // カテゴリを送ると、サーバーは記録を確定にし、店名のルールを学習する
      await TransactionService().patchTransaction(
        transaction.id,
        TransactionUpdate(
          categoryId: category.id,
          memo: memoChanged ? memo : null,
        ),
      );
      if (!mounted) return;
      setState(() {
        _confirmed[transaction.id] = category.id;
        _savedMemos[transaction.id] = memo;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _error = 'カテゴリの保存に失敗しました');
    } finally {
      if (mounted) setState(() => _saving.remove(transaction.id));
    }
  }

  // メモだけを送る。カテゴリを送らないので、確認待ちのままになる
  Future<void> _saveMemo(Transaction transaction) async {
    final memo = _memoControllers[transaction.id]!.text.trim();
    if (memo == _savedMemos[transaction.id]) return;
    setState(() {
      _saving.add(transaction.id);
      _error = null;
    });

    try {
      await TransactionService().patchTransaction(
        transaction.id,
        TransactionUpdate(memo: memo),
      );
      if (!mounted) return;
      setState(() => _savedMemos[transaction.id] = memo);
    } catch (_) {
      if (!mounted) return;
      setState(() => _error = 'メモの保存に失敗しました');
    } finally {
      if (mounted) setState(() => _saving.remove(transaction.id));
    }
  }

  Future<void> _saveAllMemos() async {
    // 保存中の行は、その保存の中でメモも送っているので飛ばす
    await Future.wait([
      for (final transaction in widget.transactions)
        if (!_saving.contains(transaction.id)) _saveMemo(transaction),
    ]);
  }

  String _formatDate(DateTime date) {
    final month = date.month.toString().padLeft(2, '0');
    final day = date.day.toString().padLeft(2, '0');
    return '${date.year}/$month/$day';
  }

  String _formatTime(TimeOfDay time) {
    final hour = time.hour.toString().padLeft(2, '0');
    final minute = time.minute.toString().padLeft(2, '0');
    return '$hour:$minute';
  }

  String _formatAmount(int amount) {
    return amount.toString().replaceAllMapped(
      RegExp(r'\B(?=(\d{3})+(?!\d))'),
      (match) => ',',
    );
  }
}
