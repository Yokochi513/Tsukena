import 'package:flutter/material.dart';
import 'package:tsukena/components/calendar/calender_month_grid.dart';

Future<DateTime?> showJapaneseDatePicker({
  required BuildContext context,
  required DateTime initialDate,
  required DateTime firstDate,
  required DateTime lastDate,
}) {
  final initial = DateUtils.dateOnly(initialDate);
  final first = DateUtils.dateOnly(firstDate);
  final last = DateUtils.dateOnly(lastDate);

  if (last.isBefore(first)) {
    throw ArgumentError('lastDate は firstDate 以降にしてください');
  }

  if (initial.isBefore(first) || initial.isAfter(last)) {
    throw ArgumentError('initialDate は選択範囲内にしてください');
  }

  return showDialog<DateTime>(
    context: context,
    builder: (_) => _JapaneseDatePickerDialog(
      initialDate: initial,
      firstDate: first,
      lastDate: last,
    ),
  );
}

class _JapaneseDatePickerDialog extends StatefulWidget {
  const _JapaneseDatePickerDialog({
    required this.initialDate,
    required this.firstDate,
    required this.lastDate,
  });

  final DateTime initialDate;
  final DateTime firstDate;
  final DateTime lastDate;

  @override
  State<_JapaneseDatePickerDialog> createState() =>
      _JapaneseDatePickerDialogState();
}

class _JapaneseDatePickerDialogState extends State<_JapaneseDatePickerDialog> {
  late DateTime _month;

  DateTime? _selectedDate;

  @override
  void initState() {
    super.initState();
    _month = DateTime(widget.initialDate.year, widget.initialDate.month);
    _selectedDate = widget.initialDate;
  }

  bool _isInRange(DateTime date) {
    return !date.isBefore(widget.firstDate) && !date.isAfter(widget.lastDate);
  }

  bool _canMoveTo(DateTime month) {
    final start = DateTime(month.year, month.month);
    final end = DateTime(month.year, month.month + 1, 0);

    return !end.isBefore(widget.firstDate) && !start.isAfter(widget.lastDate);
  }

  void _moveMonth(int offset) {
    setState(() {
      _month = DateTime(_month.year, _month.month + offset);
    });
  }

  @override
  Widget build(BuildContext context) {
    final previous = DateTime(_month.year, _month.month - 1);
    final next = DateTime(_month.year, _month.month + 1);
    final today = DateUtils.dateOnly(DateTime.now());

    return Dialog(
      child: SizedBox(
        width: 360,
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                children: [
                  IconButton(
                    tooltip: '前の月',
                    onPressed: _canMoveTo(previous)
                        ? () => _moveMonth(-1)
                        : null,
                    icon: const Icon(Icons.chevron_left),
                  ),
                  Expanded(
                    child: Text(
                      '${_month.year}年${_month.month}月',
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                  ),
                  IconButton(
                    tooltip: '次の月',
                    onPressed: _canMoveTo(next) ? () => _moveMonth(1) : null,
                    icon: const Icon(Icons.chevron_right),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              CalenderMonthGrid(
                month: _month,
                selectedDate: _selectedDate,
                firstDate: widget.firstDate,
                lastDate: widget.lastDate,
                onSelected: (date) {
                  setState(() {
                    _selectedDate = date;
                  });
                },
              ),
              const SizedBox(height: 12),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: _isInRange(today)
                        ? () {
                            setState(() {
                              _selectedDate = today;
                              _month = DateTime(today.year, today.month);
                            });
                          }
                        : null,
                    child: const Text('今日'),
                  ),
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(_selectedDate),
                    child: const Text('決定'),
                  ),
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: const Text('キャンセル'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
