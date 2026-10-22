import 'package:flutter/material.dart';
import 'package:tsukena/components/month_switcher/month_switcher.dart';
import 'package:tsukena/pages/settings_page.dart';
import 'package:tsukena/features/income/entities/income.dart';
import 'package:tsukena/features/income/repositories/income_repository.dart';
import 'package:tsukena/features/income/widgets/incomes_list.dart';
import 'package:tsukena/features/income/widgets/income_edit_dailog.dart';

/// 月の収入の一覧（入金日の月で絞る）。月はホームの画面が持ち、月の画面・支出の一覧と共有する
class IncomeListPage extends StatefulWidget {
  const IncomeListPage({
    super.key,
    required this.month,
    required this.onMonthChanged,
  });

  final DateTime month;
  final ValueChanged<DateTime> onMonthChanged;

  @override
  State<IncomeListPage> createState() => _ExpenseListPageState();
}

class _ExpenseListPageState extends State<IncomeListPage> {
  late Future<List<Income>> _incomes;

  @override
  initState() {
    super.initState();
    _reload();
  }

  @override
  void didUpdateWidget(IncomeListPage oldWidget) {
    super.didUpdateWidget(oldWidget);
    // build の途中で呼ばれるので setState は要らない
    if (widget.month != oldWidget.month) _incomes = _fetch();
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
            child: FutureBuilder<List<Income>>(
              future: _incomes,
              builder: (context, snapshot) {
                if (snapshot.connectionState != ConnectionState.done) {
                  return const Center(child: CircularProgressIndicator());
                }

                if (snapshot.hasError) {
                  return const Center(child: Text('収入の取得に失敗しました'));
                }
                return IncomeList(
                  incomes: snapshot.data ?? [],
                  onTap: _openEdit,
                );
              },
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        tooltip: '収入を追加',
        onPressed: () => _openEdit(null),
        child: const Icon(Icons.add),
      ),
    );
  }

  Future<void> _openEdit(Income? income) async {
    final saved = await showDialog<bool>(
      context: context,
      builder: (_) => IncomeEditDialog(income: income),
    );
    if (saved == true) _reload();
  }

  void _reload() {
    setState(() {
      _incomes = _fetch();
    });
  }

  Future<List<Income>> _fetch() {
    return IncomeService().getIncomes(formatYearMonth(widget.month));
  }
}
