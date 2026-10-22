import 'package:flutter/material.dart';
import 'package:tsukena/features/month_summary/entities/monthly_summary.dart';
import 'package:tsukena/features/month_summary/repositories/month_summary_repository.dart';
import 'package:tsukena/features/month_summary/widgets/monthly_summary_view.dart';
import 'package:tsukena/pages/settings_page.dart';

// TODO: 支出・収入の一覧が月で絞り込めるようになったら、合計から各一覧へ移れるようにする（→ docs/design.md 5.1）
/// 起動時の画面。月を切り替えて、その月の収支・予算の残り・カテゴリ別の内訳を見る
class MonthPage extends StatefulWidget {
  const MonthPage({super.key});

  @override
  State<MonthPage> createState() => _MonthPageState();
}

class _MonthPageState extends State<MonthPage> {
  // 日は使わない。月を足し引きしやすいよう、常に1日にしておく
  DateTime _month = _thisMonth();
  late Future<MonthlySummary> _summary;

  static DateTime _thisMonth() {
    final now = DateTime.now();
    return DateTime(now.year, now.month);
  }

  @override
  initState() {
    super.initState();
    _summary = _fetch();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('月の収支'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: '読み込み',
            onPressed: _reload,
          ),
          const SettingsButton(),
        ],
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 600),
          child: ListView(
            padding: const EdgeInsets.only(bottom: 16),
            children: [
              _monthSwitcher(context),
              FutureBuilder<MonthlySummary>(
                future: _summary,
                builder: (context, snapshot) {
                  if (snapshot.connectionState != ConnectionState.done) {
                    return const Padding(
                      padding: EdgeInsets.all(32),
                      child: Center(child: CircularProgressIndicator()),
                    );
                  }
                  final summary = snapshot.data;
                  if (snapshot.hasError || summary == null) {
                    return const Padding(
                      padding: EdgeInsets.all(32),
                      child: Center(child: Text('月の集計の取得に失敗しました')),
                    );
                  }
                  return MonthlySummaryView(summary: summary);
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _monthSwitcher(BuildContext context) {
    final isThisMonth = _month == _thisMonth();

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8),
      child: Row(
        children: [
          IconButton(
            icon: const Icon(Icons.chevron_left),
            tooltip: '前の月',
            onPressed: () => _moveMonth(-1),
          ),
          Expanded(
            child: Text(
              '${_month.year}年${_month.month}月',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.titleLarge,
            ),
          ),
          // 来月以降もカードの引き落としを見るために開ける（→ docs/design.md 4.3）
          IconButton(
            icon: const Icon(Icons.chevron_right),
            tooltip: '次の月',
            onPressed: () => _moveMonth(1),
          ),
          TextButton(
            onPressed: isThisMonth ? null : () => _showMonth(_thisMonth()),
            child: const Text('今月'),
          ),
        ],
      ),
    );
  }

  void _moveMonth(int delta) {
    // DateTime は 13月や 0月を、年をまたいだ月に直してくれる
    _showMonth(DateTime(_month.year, _month.month + delta));
  }

  void _showMonth(DateTime month) {
    setState(() {
      _month = month;
      _summary = _fetch();
    });
  }

  void _reload() {
    setState(() {
      _summary = _fetch();
    });
  }

  Future<MonthlySummary> _fetch() {
    final year = _month.year.toString().padLeft(4, '0');
    final month = _month.month.toString().padLeft(2, '0');
    return MonthSummaryService().getMonthlySummary('$year-$month');
  }
}
