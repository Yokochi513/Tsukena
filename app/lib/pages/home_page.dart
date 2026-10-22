import 'package:flutter/material.dart';
import 'package:tsukena/pages/month_page.dart';
import 'package:tsukena/pages/transaction_list_page.dart';
import 'package:tsukena/pages/income_list_page.dart';

/// 下のタブでは、毎日見る記録の画面だけを切り替える。設定はたまにしか開かないので、各画面の右上から開く
class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  int _selectedIndex = 1;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _selectedIndex,
        children: [TransactionListPage(), MonthPage(), IncomeListPage()],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: (index) {
          setState(() {
            _selectedIndex = index;
          });
        },
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
}
