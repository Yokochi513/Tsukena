import 'package:flutter/material.dart';
import 'package:tsukena/components/month_switcher/month_switcher.dart';
import 'package:tsukena/features/month_summary/entities/monthly_summary.dart';
import 'package:tsukena/features/month_summary/repositories/month_summary_repository.dart';
import 'package:tsukena/features/month_summary/widgets/monthly_summary_view.dart';
import 'package:tsukena/features/transaction/entities/transaction.dart';
import 'package:tsukena/features/transaction/repositories/transaction_repository.dart';
import 'package:tsukena/features/transaction/widgets/transaction_brief_sheet.dart';
import 'package:tsukena/pages/settings_page.dart';

/// 起動時の画面。月を切り替えて、その月の収支・予算の残り・カテゴリ別の内訳を見る。
///
/// 月はホームの画面が持ち、支出・収入の一覧と共有する。収入・支出の行を押すと、同じ月の一覧へ移る
class MonthPage extends StatefulWidget {
  const MonthPage({
    super.key,
    required this.month,
    required this.onMonthChanged,
    this.onOpenTransactions,
    this.onOpenIncomes,
  });

  final DateTime month;
  final ValueChanged<DateTime> onMonthChanged;
  final VoidCallback? onOpenTransactions;
  final VoidCallback? onOpenIncomes;

  @override
  State<MonthPage> createState() => _MonthPageState();
}

class _MonthPageState extends State<MonthPage> {
  late Future<MonthlySummary> _summary;

  @override
  initState() {
    super.initState();
    _summary = _fetch();
  }

  @override
  void didUpdateWidget(MonthPage oldWidget) {
    super.didUpdateWidget(oldWidget);
    // build の途中で呼ばれるので setState は要らない
    if (widget.month != oldWidget.month) _summary = _fetch();
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
              MonthSwitcher(
                month: widget.month,
                onChanged: widget.onMonthChanged,
              ),
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
                  return MonthlySummaryView(
                    summary: summary,
                    onTapIncome: widget.onOpenIncomes,
                    onTapExpense: widget.onOpenTransactions,
                    onTapCategory: _showCategory,
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// カテゴリの内訳の明細を、下からのシートで手短に見せる
  void _showCategory(CategoryTotal item) {
    final category = item.category;
    // builder はシートが描き直されるたびに呼ばれるので、取得はその外で1回だけ始める
    final transactions = _fetchCategory(category?.id);
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (_) => TransactionBriefSheet(
        title: category == null
            ? '❓ 未分類（確認待ち）'
            : '${category.emoji} ${category.name}',
        month: widget.month,
        transactions: transactions,
        // 支払日を直すと月の集計が変わる。シートの後ろの集計も取り直しておく
        onPaidDateChanged: _reload,
      ),
    );
  }

  /// 集計と同じ数え方で、その月のそのカテゴリの支出を取る。
  /// 集計では確認待ちを、カテゴリが付いていても未分類にまとめる（→ docs/module/model_design.md の CategoryTotal）
  Future<List<Transaction>> _fetchCategory(int? categoryId) async {
    final transactions = await TransactionService().getTransactions(
      month: formatYearMonth(widget.month),
    );
    return transactions.where((t) {
      if (categoryId == null) return t.status == TransactionStatus.pending;
      return t.status == TransactionStatus.confirmed &&
          t.categoryId == categoryId;
    }).toList();
  }

  void _reload() {
    setState(() {
      _summary = _fetch();
    });
  }

  Future<MonthlySummary> _fetch() {
    return MonthSummaryService().getMonthlySummary(
      formatYearMonth(widget.month),
    );
  }
}
