import 'dart:async';

import 'package:flutter/material.dart';
import 'package:tsukena/features/transaction/entities/category.dart';
import 'package:tsukena/features/transaction/entities/transaction.dart';
import 'package:tsukena/features/transaction/repositories/category_repository.dart';
import 'package:tsukena/features/transaction/repositories/transaction_repository.dart';
import 'package:tsukena/features/transaction/widgets/transaction_edit_dialog.dart';
import 'package:tsukena/features/transaction/widgets/transaction_list.dart';

/// 店名かメモで支出を探す。「このお店にいくら使ったか」に答えられるよう、月で絞らず全期間から探し、件数と合計を出す
class TransactionSearchPage extends StatefulWidget {
  const TransactionSearchPage({super.key});

  @override
  State<TransactionSearchPage> createState() => _TransactionSearchPageState();
}

class _TransactionSearchPageState extends State<TransactionSearchPage> {
  // 1文字打つごとに問い合わせないよう、打ち終わるまで少し待つ
  static const _debounce = Duration(milliseconds: 300);

  final _categories = CategoryService().getCategories().then(
    (categories) => {for (final c in categories) c.id: c},
  );
  Timer? _timer;
  String _query = '';
  Future<List<Transaction>>? _results;

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: TextField(
          autofocus: true,
          decoration: const InputDecoration(
            hintText: '店名・メモで探す',
            border: InputBorder.none,
          ),
          textInputAction: TextInputAction.search,
          onChanged: _onChanged,
        ),
      ),
      body: _body(context),
    );
  }

  Widget _body(BuildContext context) {
    final results = _results;
    if (results == null) {
      return const Center(child: Text('すべての月の支出から探します'));
    }

    return FutureBuilder(
      future: (results, _categories).wait,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return const Center(child: Text('支出の検索に失敗しました'));
        }

        final (transactions, categoryMap) = snapshot.requireData;
        if (transactions.isEmpty) {
          return Center(child: Text('「$_query」に当てはまる支出はありません'));
        }

        final total = transactions.fold(0, (sum, t) => sum + t.amount);
        return Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
              child: Text(
                '${transactions.length}件・合計 ¥${_formatAmount(total)}',
                style: Theme.of(context).textTheme.titleMedium,
              ),
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
    );
  }

  void _onChanged(String value) {
    _timer?.cancel();
    _timer = Timer(_debounce, () {
      final query = value.trim();
      setState(() {
        _query = query;
        _results = query.isEmpty
            ? null
            : TransactionService().getTransactions(q: query);
      });
    });
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
    // 直した結果、検索に当てはまらなくなることもあるので、同じ語で探し直す
    if (saved == true && _query.isNotEmpty) {
      setState(() {
        _results = TransactionService().getTransactions(q: _query);
      });
    }
  }

  String _formatAmount(int amount) {
    return amount.toString().replaceAllMapped(
      RegExp(r'\B(?=(\d{3})+(?!\d))'),
      (match) => ',',
    );
  }
}
