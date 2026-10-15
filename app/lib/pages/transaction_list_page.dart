import 'dart:core';

import 'package:flutter/material.dart';
import 'package:tsukena/features/transaction/entities/transaction.dart';
import 'package:tsukena/features/transaction/entities/category.dart';
import 'package:tsukena/features/transaction/repositories/category_repository.dart';
import 'package:tsukena/features/transaction/repositories/transaction_repository.dart';
import 'package:tsukena/features/transaction/widgets/transaction_list.dart';

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
        title: const Text('取引一覧'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: '取引読み込み',
            onPressed: () {
              _reload();
            },
          ),
        ],
      ),
      body: FutureBuilder(
        future: _data,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }

          if (snapshot.hasError) {
            return const Center(child: Text('取引の取得に失敗しました'));
          }

          final (transactions, categoryMap) = snapshot.requireData;
          return TransactionList(
            transactions: transactions,
            categories: categoryMap,
          );
        },
      ),
    );
  }

  Future<(List<Transaction>, Map<int, Category>)> _load() async {
    const baseUrl = 'http://127.0.0.1:8000';
    // 二つのAPIが終わるまで待つ
    final (transactions, categories) = await (
      TransactionService(baseUrl: baseUrl).getTransactions(),
      CategoryService(baseUrl: baseUrl).getCategories(),
    ).wait;
    return (transactions, {for (final c in categories) c.id: c});
  }

  void _reload() {
    setState(() {
      _data = _load();
    });
  }
}
