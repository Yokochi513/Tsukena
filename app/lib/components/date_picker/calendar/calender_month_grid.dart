import 'package:flutter/material.dart';
import 'package:tsukena/components/date_picker/calendar/month_cells.dart';

class CalenderMonthGrid extends StatelessWidget {
  const CalenderMonthGrid({
    super.key,
    required this.month,
    required this.selectedDate,
    required this.firstDate,
    required this.lastDate,
    required this.onSelected,
  });

  final DateTime month;
  final DateTime? selectedDate;
  final DateTime firstDate;
  final DateTime lastDate;
  final ValueChanged<DateTime> onSelected;

  @override
  Widget build(BuildContext context) {
    final cells = monthCells(month);
    final today = DateTime.now();
    final colors = Theme.of(context).colorScheme;

    Color weekdayColor(int column) {
      if (column == 0) return Colors.red;
      if (column == 6) return Colors.blue;
      return colors.onSurface;
    }

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          children: [
            for (final (index, label) in [
              '日',
              '月',
              '火',
              '水',
              '木',
              '金',
              '土',
            ].indexed)
              Expanded(
                child: Center(
                  child: Text(
                    label,
                    style: TextStyle(color: weekdayColor(index)),
                  ),
                ),
              ),
          ],
        ),
        const SizedBox(height: 8),
        GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: cells.length,
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 7,
          ),
          itemBuilder: (context, index) {
            final date = cells[index];

            if (date == null) return const SizedBox.shrink();
            final isEnabled =
                !date.isBefore(DateUtils.dateOnly(firstDate)) &&
                !date.isAfter(DateUtils.dateOnly(lastDate));

            final isToday = DateUtils.isSameDay(date, today);
            final isSelected = DateUtils.isSameDay(date, selectedDate);

            return Padding(
              padding: const EdgeInsets.all(3),
              child: Material(
                color: isSelected ? colors.primary : Colors.transparent,
                shape: CircleBorder(
                  side: isToday
                      ? BorderSide(color: colors.primary, width: 2)
                      : BorderSide.none,
                ),
                clipBehavior: Clip.antiAlias,
                child: InkWell(
                  onTap: isEnabled ? () => onSelected(date) : null,
                  child: Center(
                    child: Text(
                      '${date.day}',
                      style: TextStyle(
                        color: !isEnabled
                            ? colors.onSurface.withValues(alpha: 0.38)
                            : isSelected
                            ? colors.onPrimary
                            : weekdayColor(index % 7),
                      ),
                    ),
                  ),
                ),
              ),
            );
          },
        ),
      ],
    );
  }
}
