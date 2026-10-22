import 'package:flutter/material.dart';
import 'package:tsukena/features/month_summary/entities/monthly_summary.dart';

/// 月の集計を、予算の残り・収支・カテゴリ別の内訳の順に並べる。画面の ListView の中に置くため、自分ではスクロールしない
class MonthlySummaryView extends StatelessWidget {
  const MonthlySummaryView({super.key, required this.summary});

  final MonthlySummary summary;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _budgetCard(context),
        _balanceCard(context),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 4),
          child: Text('カテゴリ別', style: textTheme.titleMedium),
        ),
        if (summary.byCategory.isEmpty)
          const ListTile(title: Text('この月の支出はありません'))
        else
          for (final item in summary.byCategory) _categoryRow(context, item),
      ],
    );
  }

  Widget _budgetCard(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final colorScheme = Theme.of(context).colorScheme;
    final over = summary.remaining < 0;

    return Card(
      margin: const EdgeInsets.fromLTRB(16, 8, 16, 0),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(over ? '予算を超えた分' : '予算の残り', style: textTheme.labelLarge),
            const SizedBox(height: 4),
            Text(
              '¥${_formatAmount(summary.remaining.abs())}',
              style: textTheme.headlineMedium?.copyWith(
                color: over ? colorScheme.error : null,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 12),
            LinearProgressIndicator(
              value: (summary.total / summary.budget).clamp(0, 1).toDouble(),
              minHeight: 8,
              borderRadius: BorderRadius.circular(4),
              color: over ? colorScheme.error : null,
            ),
            const SizedBox(height: 8),
            Text(
              '支出 ¥${_formatAmount(summary.total)} / 予算 ¥${_formatAmount(summary.budget)}',
              style: textTheme.bodySmall,
            ),
          ],
        ),
      ),
    );
  }

  Widget _balanceCard(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final colorScheme = Theme.of(context).colorScheme;

    Widget row(String label, String value, {Color? color}) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          children: [
            Expanded(child: Text(label)),
            Text(value, style: textTheme.titleMedium?.copyWith(color: color)),
          ],
        ),
      );
    }

    final balance = summary.balance;
    return Card(
      margin: const EdgeInsets.fromLTRB(16, 8, 16, 0),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Column(
          children: [
            row('収入', '¥${_formatAmount(summary.incomeTotal)}'),
            row('支出', '¥${_formatAmount(summary.total)}'),
            const Divider(),
            row(
              '収支',
              '${balance < 0 ? '−' : '+'}¥${_formatAmount(balance.abs())}',
              color: balance < 0 ? colorScheme.error : null,
            ),
          ],
        ),
      ),
    );
  }

  Widget _categoryRow(BuildContext context, CategoryTotal item) {
    final textTheme = Theme.of(context).textTheme;
    final category = item.category;
    // 支出合計に占める割合を棒で見せる。並びは金額の多い順なので、上ほど長い
    final ratio = summary.total == 0 ? 0.0 : item.amount / summary.total;

    return ListTile(
      leading: Text(category?.emoji ?? '❓', style: textTheme.titleLarge),
      title: Row(
        children: [
          Expanded(child: Text(category?.name ?? '未分類（確認待ち）')),
          Text('¥${_formatAmount(item.amount)}'),
        ],
      ),
      subtitle: Padding(
        padding: const EdgeInsets.only(top: 4),
        child: LinearProgressIndicator(
          value: ratio,
          minHeight: 4,
          borderRadius: BorderRadius.circular(2),
          color: category == null
              ? Theme.of(context).colorScheme.outline
              : null,
        ),
      ),
    );
  }

  String _formatAmount(int amount) {
    return amount.toString().replaceAllMapped(
      RegExp(r'\B(?=(\d{3})+(?!\d))'),
      (match) => ',',
    );
  }
}
