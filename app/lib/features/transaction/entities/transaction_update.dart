// 取引の修正で送る内容。null の項目は送らず、サーバーも変えない
class TransactionUpdate {
  DateTime? occurredDate;
  DateTime? paidDate;
  int? amount;
  String? merchant;
  String? memo;
  int? categoryId;

  TransactionUpdate({
    this.occurredDate,
    this.paidDate,
    this.amount,
    this.merchant,
    this.memo,
    this.categoryId,
  });

  Map<String, dynamic> toJson() => {
    'occurred_date': ?_formatDate(occurredDate),
    'paid_date': ?_formatDate(paidDate),
    'amount': ?amount,
    'merchant': ?merchant,
    'memo': ?memo,
    'category_id': ?categoryId,
  };

  static String? _formatDate(DateTime? date) {
    if (date == null) return null;
    final month = date.month.toString().padLeft(2, '0');
    final day = date.day.toString().padLeft(2, '0');
    return '${date.year}-$month-$day';
  }
}
