import 'dart:core';

import 'package:flutter/material.dart';
import 'package:tsukena/pages/settings_page.dart';
import 'package:tsukena/components/show_modal_top_sheet/show_modal_top_sheet.dart';
import 'package:tsukena/features/transaction/entities/transaction.dart';
import 'package:tsukena/features/transaction/entities/category.dart';
import 'package:tsukena/features/transaction/repositories/category_repository.dart';
import 'package:tsukena/features/transaction/repositories/transaction_repository.dart';
import 'package:tsukena/features/transaction/widgets/transaction_edit_dialog.dart';
import 'package:tsukena/features/transaction/widgets/transaction_list.dart';
import 'package:tsukena/features/transaction/widgets/transaction_pending_banner.dart';
import 'package:tsukena/features/transaction/widgets/transaction_pending_sheet.dart';

class TransactionListPage extends StatefulWidget {
  const TransactionListPage({super.key});

  @override
  State<TransactionListPage> createState() => _TransactionListPageState();
}

class _TransactionListPageState extends State<TransactionListPage> {
  late Future<(List<Transaction>, Map<int, Category>)> _data;

  @override
  initState() {
    super.initState();
    _data = _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('支出一覧'),
        actions: [
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
      body: FutureBuilder(
        future: _data,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }

          if (snapshot.hasError) {
            return const Center(child: Text('支出の取得に失敗しました'));
          }

          final (transactions, categoryMap) = snapshot.requireData;
          final pending = transactions
              .where((t) => t.status == TransactionStatus.pending)
              .toList();

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
                  onTap: (transaction) => _openEdit(transaction, categoryMap),
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  Future<(List<Transaction>, Map<int, Category>)> _load() async {
    // 二つのAPIが終わるまで待つ
    final (transactions, categories) = await (
      TransactionService().getTransactions(),
      CategoryService().getCategories(),
    ).wait;
    return (transactions, {for (final c in categories) c.id: c});
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
