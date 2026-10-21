import 'package:flutter/material.dart';
import 'package:tsukena/components/date_picker/calendar/japanese_date_picker.dart';

class DatePickerField extends StatelessWidget {
  const DatePickerField({
    super.key,
    required this.label,
    required this.value,
    required this.onChanged,
  });

  final String label;
  final DateTime value;
  final ValueChanged<DateTime> onChanged;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: () async {
        final picked = await showJapaneseDatePicker(
          context: context,
          initialDate: value,
          firstDate: DateTime(0),
          lastDate: DateTime.now().add(const Duration(days: 360)),
        );
        if (picked != null) onChanged(picked);
      },
      child: InputDecorator(
        decoration: InputDecoration(labelText: label),
        child: Text('${value.year}/${value.month}/${value.day}'),
      ),
    );
  }
}
