import 'package:flutter/material.dart';
import 'package:tsukena/features/income/entities/income.dart';
import 'package:tsukena/features/income/repositories/income_repository.dart';
import 'package:tsukena/features/income/widgets/incomes_list.dart';

class IncomeListPage extends StatefulWidget {
  const IncomeListPage({super.key});

  @override
  State<IncomeListPage> createState() => _ExpenseListPageState();
}

class _ExpenseListPageState extends State<IncomeListPage> {
  late Future<List<Income>> _incomes;

  @override
  initState() {
    super.initState();
    _incomes = IncomeService(baseUrl: 'http://127.0.0.1:8000').getIncomes();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('収入一覧'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: '収入読み込み',
            onPressed: () {
              setState(() {
                _incomes = IncomeService(
                  baseUrl: 'http://127.0.0.1:8000',
                ).getIncomes();
              });
            },
          ),
        ],
      ),
      body: FutureBuilder<List<Income>>(
        future: _incomes,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }

          if (snapshot.hasError) {
            return const Center(child: Text('収入の取得に失敗しました'));
          }
          return IncomeList(incomes: snapshot.data ?? []);
        },
      ),
    );
  }
}
