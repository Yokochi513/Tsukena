import 'package:flutter/material.dart';
import 'package:tsukena/components/month_switcher/month_switcher.dart';
import 'package:tsukena/pages/month_page.dart';
import 'package:tsukena/pages/transaction_list_page.dart';
import 'package:tsukena/pages/income_list_page.dart';

/// 下のタブでは、毎日見る記録の画面だけを切り替える。設定はたまにしか開かないので、各画面の右上から開く。
///
/// 見ている月はここで1つだけ持ち、3つのタブで共有する。月の画面で月を変えてから一覧へ移っても、同じ月が開く
class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  static const _transactionsTab = 0;
  static const _monthTab = 1;
  static const _incomesTab = 2;

  int _selectedIndex = _monthTab;
  DateTime _month = thisMonth();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _selectedIndex,
        children: [
          TransactionListPage(month: _month, onMonthChanged: _changeMonth),
          MonthPage(
            month: _month,
            onMonthChanged: _changeMonth,
            onOpenTransactions: () => _selectTab(_transactionsTab),
            onOpenIncomes: () => _selectTab(_incomesTab),
          ),
          IncomeListPage(month: _month, onMonthChanged: _changeMonth),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: _selectTab,
        destinations: [
          NavigationDestination(
            icon: Icon(Icons.payment_outlined),
            selectedIcon: Icon(Icons.payments),
            label: '支出',
          ),
          NavigationDestination(
            icon: Icon(Icons.calendar_month_outlined),
            selectedIcon: Icon(Icons.calendar_month),
            label: '月',
          ),
          NavigationDestination(
            icon: Icon(Icons.account_balance_wallet_outlined),
            selectedIcon: Icon(Icons.account_balance_wallet),
            label: '収入',
          ),
        ],
      ),
    );
  }

  void _selectTab(int index) {
    setState(() {
      _selectedIndex = index;
    });
  }

  void _changeMonth(DateTime month) {
    setState(() {
      _month = month;
    });
  }
}
