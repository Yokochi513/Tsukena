import 'package:tsukena/features/income/entities/income.dart';
import 'package:tsukena/features/transaction/entities/category.dart';
import 'package:tsukena/features/transaction/entities/transaction.dart';

/// 月の明細（支出と収入）を CSV にする。
///
/// 金額は月の集計と同じ数え方にする。分割などは、その月の引き落とし額（手数料を含む）を出す。
/// 日付は、支出ならその月の引き落とし日、収入なら入金日。行は日付の順に並べる。
///
/// Excel で開いても文字化けしないよう、先頭に BOM を付ける。改行は CRLF にする
String buildMonthCsv({
  required DateTime month,
  required List<Transaction> transactions,
  required List<Income> incomes,
  required List<Category> categories,
}) {
  final categoryNames = {for (final c in categories) c.id: c.name};

  final rows = <_Row>[
    for (final t in transactions) _expenseRow(t, month, categoryNames),
    for (final i in incomes)
      _Row(i.receivedDate, [
        '収入',
        _formatDate(i.receivedDate),
        '',
        '',
        '',
        '${i.amount}',
        '',
        '',
        '',
        '',
        i.memo,
      ]),
  ]..sort((a, b) => a.date.compareTo(b.date));

  const header = [
    '種別',
    '日付',
    '利用日',
    '店名',
    'カテゴリ',
    '金額',
    '利用額',
    '支払い方法',
    '支払い手段',
    '状態',
    'メモ',
  ];
  final lines = [
    header,
    for (final r in rows) r.fields,
  ].map((fields) => fields.map(_escape).join(','));
  return '﻿${lines.join('\r\n')}\r\n';
}

_Row _expenseRow(
  Transaction t,
  DateTime month,
  Map<int, String> categoryNames,
) {
  final date = t.chargesIn(month).firstOrNull?.paidDate ?? t.paidDate;
  return _Row(date, [
    '支出',
    _formatDate(date),
    _formatDate(t.occurredDate),
    t.merchant,
    categoryNames[t.categoryId] ?? '',
    '${t.amountIn(month)}',
    '${t.amount}',
    t.planLabelIn(month) ?? t.paymentPlan.label,
    t.paymentMethod,
    t.status == TransactionStatus.pending ? '確認待ち' : '',
    t.memo,
  ]);
}

class _Row {
  _Row(this.date, this.fields);

  final DateTime date;
  final List<String> fields;
}

String _formatDate(DateTime date) {
  final m = date.month.toString().padLeft(2, '0');
  final d = date.day.toString().padLeft(2, '0');
  return '${date.year}-$m-$d';
}

// カンマ・ダブルクォート・改行（メモは複数行になる）を含む値は、ダブルクォートで囲む
String _escape(String value) {
  if (!value.contains(RegExp(r'[",\r\n]'))) return value;
  return '"${value.replaceAll('"', '""')}"';
}
