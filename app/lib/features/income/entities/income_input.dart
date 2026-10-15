class IncomeInput {
  DateTime receivedDate = DateTime.now();
  int amount = 0;
  String memo = '';

  Map<String, dynamic> toJson() {
    final month = receivedDate.month.toString().padLeft(2, '0');
    final day = receivedDate.day.toString().padLeft(2, '0');
    return {
      'received_date': '${receivedDate.year}-$month-$day',
      'amount': amount,
      'memo': memo,
    };
  }
}
