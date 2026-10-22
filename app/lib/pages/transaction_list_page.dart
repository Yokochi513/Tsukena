import 'dart:core';

import 'package:flutter/material.dart';
import 'package:tsukena/components/month_switcher/month_switcher.dart';
import 'package:tsukena/components/show_modal_top_sheet/show_modal_top_sheet.dart';
import 'package:tsukena/pages/settings_page.dart';
import 'package:tsukena/pages/transaction_search_page.dart';
import 'package:tsukena/features/transaction/entities/transaction.dart';
import 'package:tsukena/features/transaction/entities/category.dart';
import 'package:tsukena/features/transaction/repositories/category_repository.dart';
import 'package:tsukena/features/transaction/repositories/transaction_repository.dart';
import 'package:tsukena/features/transaction/widgets/transaction_edit_dialog.dart';
import 'package:tsukena/features/transaction/widgets/transaction_list.dart';
import 'package:tsukena/features/transaction/widgets/transaction_pending_banner.dart';
import 'package:tsukena/features/transaction/widgets/transaction_pending_sheet.dart';

/// 月の支出の明細（支払日の月で絞る）。月はホームの画面が持ち、月の画面・収入の一覧と共有する
class TransactionListPage extends StatefulWidget {
  const TransactionListPage({
    super.key,
    required this.month,
    required this.onMonthChanged,
  });

  final DateTime month;
  final ValueChanged<DateTime> onMonthChanged;

  @override
  State<TransactionListPage> createState() => _TransactionListPageState();
}

class _TransactionListPageState extends State<TransactionListPage> {
  late Future<(List<Transaction>, List<Transaction>, Map<int, Category>)> _data;

  @override
  initState() {
    super.initState();
    _data = _load();
  }

  @override
  void didUpdateWidget(TransactionListPage oldWidget) {
    super.didUpdateWidget(oldWidget);
    // build の途中で呼ばれるので setState は要らない
    if (widget.month != oldWidget.month) _data = _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('支出一覧'),
        actions: [
          IconButton(
            icon: const Icon(Icons.search),
            tooltip: '支出を探す',
            onPressed: _openSearch,
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: '支出読み込み',
            onPressed: () {
              _reload();
            },
          ),
          const SettingsButton(),
        ],
      ),
      // 月の切り替えは読み込み中も出しておき、続けて月を送れるようにする
      body: Column(
        children: [
          MonthSwitcher(month: widget.month, onChanged: widget.onMonthChanged),
          Expanded(
            child: FutureBuilder(
              future: _data,
              builder: (context, snapshot) {
                if (snapshot.connectionState != ConnectionState.done) {
                  return const Center(child: CircularProgressIndicator());
                }

                if (snapshot.hasError) {
                  return const Center(child: Text('支出の取得に失敗しました'));
                }

                final (transactions, pending, categoryMap) =
                    snapshot.requireData;

                return Column(
                  children: [
                    if (pending.isNotEmpty)
                      TransactionPendingBanner(
                        count: pending.length,
                        onTap: () => _openPending(pending, categoryMap),
                      ),
                    Expanded(
                      child: TransactionList(
                        transactions: transactions,
                        categories: categoryMap,
                        onTap: (transaction) =>
                            _openEdit(transaction, categoryMap),
                      ),
                    ),
                  ],
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Future<(List<Transaction>, List<Transaction>, Map<int, Category>)>
  _load() async {
    // 確認待ちは月をまたいで溜まるため、明細とは別に月で絞らずに取る（→ docs/api_list.md 2.2）
    final service = TransactionService();
    final (transactions, pending, categories) = await (
      service.getTransactions(month: formatYearMonth(widget.month)),
      service.getTransactions(status: TransactionStatus.pending),
      CategoryService().getCategories(),
    ).wait;
    return (transactions, pending, {for (final c in categories) c.id: c});
  }

  Future<void> _openEdit(
    Transaction transaction,
    Map<int, Category> categories,
  ) async {
    final saved = await showDialog<bool>(
      context: context,
      builder: (_) => TransactionEditDialog(
        transaction: transaction,
        categories: categories,
      ),
    );
    if (saved == true) _reload();
  }

  Future<void> _openSearch() async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(builder: (_) => const TransactionSearchPage()),
    );
    // 検索の画面で直した支出を、一覧にも映す
    _reload();
  }

  void _reload() {
    setState(() {
      _data = _load();
    });
  }

  Future<void> _openPending(
    List<Transaction> pending,
    Map<int, Category> categories,
  ) async {
    await showModalTopSheet<void>(
      context: context,
      builder: (_) => TransactionPendingSheet(
        transactions: pending,
        categories: categories,
      ),
    );
    // 幕を押して閉じたときは値が返らないため、確定したかどうかに関わらず読み直す
    _reload();
  }
}
