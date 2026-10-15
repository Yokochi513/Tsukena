import 'package:flutter/material.dart';
import 'package:tsukena/features/expense/entities/expense.dart';
import 'package:tsukena/features/expense/repositories/expense_repository.dart';
import 'package:tsukena/features/expense/widgets/expense_list.dart';

class ExpenseListPage extends StatefulWidget {
  const ExpenseListPage({super.key});

  @override
  State<ExpenseListPage> createState() => _ExpenseListPageState();
}

class _ExpenseListPageState extends State<ExpenseListPage> {
  late Future<List<Expense>> _expenses;

  @override
  initState() {
    super.initState();
    _expenses = ExpenseService(baseUrl: 'http://127.0.0.1:8000').getExpenses();
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
              setState(() {
                _expenses = ExpenseService(
                  baseUrl: 'http://127.0.0.1:8000',
                ).getExpenses();
              });
            },
          ),
        ],
      ),
      body: FutureBuilder<List<Expense>>(
        future: _expenses,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }

          if (snapshot.hasError) {
            return const Center(child: Text('支出の取得に失敗しました'));
          }
          return ExpenseList(expenses: snapshot.data ?? []);
        },
      ),
    );
  }
}
