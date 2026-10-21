List<DateTime?> monthCells(DateTime month) {
  final firstDay = DateTime(month.year, month.month, 1);
  final offset = firstDay.weekday % 7;
  final daysInMonth = DateTime(month.year, month.month + 1, 0).day;

  return List<DateTime?>.generate(42, (index) {
    final day = index - offset + 1;

    if (day < 1 || day > daysInMonth) {
      return null;
    }

    return DateTime(month.year, month.month, day);
  });
}
