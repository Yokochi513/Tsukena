import 'package:flutter/material.dart';

/// 月の初日。日は使わず、月を足し引きしやすいよう常に1日にしておく
DateTime thisMonth() {
  final now = DateTime.now();
  return DateTime(now.year, now.month);
}

/// API に渡す月の形（"YYYY-MM"）
String formatYearMonth(DateTime month) {
  final year = month.year.toString().padLeft(4, '0');
  final m = month.month.toString().padLeft(2, '0');
  return '$year-$m';
}

/// 「‹ 2026年10月 › 今月」の行。月の画面と、支出・収入の一覧で使う
class MonthSwitcher extends StatelessWidget {
  const MonthSwitcher({
    super.key,
    required this.month,
    required this.onChanged,
  });

  /// 表示している月の初日
  final DateTime month;
  final ValueChanged<DateTime> onChanged;

  @override
  Widget build(BuildContext context) {
    final isThisMonth = month == thisMonth();

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8),
      child: Row(
        children: [
          IconButton(
            icon: const Icon(Icons.chevron_left),
            tooltip: '前の月',
            onPressed: () => _move(-1),
          ),
          Expanded(
            child: Text(
              '${month.year}年${month.month}月',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.titleLarge,
            ),
          ),
          // 来月以降もカードの引き落としを見るために開ける（→ docs/design.md 4.3）
          IconButton(
            icon: const Icon(Icons.chevron_right),
            tooltip: '次の月',
            onPressed: () => _move(1),
          ),
          TextButton(
            onPressed: isThisMonth ? null : () => onChanged(thisMonth()),
            child: const Text('今月'),
          ),
        ],
      ),
    );
  }

  // DateTime は 13月や 0月を、年をまたいだ月に直してくれる
  void _move(int delta) => onChanged(DateTime(month.year, month.month + delta));
}
