import 'package:flutter/material.dart';
import 'package:tsukena/features/income/entities/income.dart';

class IncomeList extends StatelessWidget {
  const IncomeList({super.key, required this.incomes});

  final List<Income> incomes;

  @override
  Widget build(BuildContext context) {
    if (incomes.isEmpty) {
      return const Center(child: Text('収入がありません'));
    }

    final textTheme = Theme.of(context).textTheme;

    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 600),
        child: ListView.separated(
          padding: const EdgeInsets.symmetric(vertical: 8),
          itemCount: incomes.length,
          separatorBuilder: (context, index) => const Divider(height: 1),
          itemBuilder: (context, index) {
            final income = incomes[index];

            return ListTile(
              title: Text(income.memo.isEmpty ? '（メモなし）' : income.memo),
              subtitle: Text(_formatDate(income.receivedDate)),
              trailing: Text(
                '¥${_formatAmount(income.amount)}',
                style: textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  String _formatDate(DateTime date) {
    final month = date.month.toString().padLeft(2, '0');
    final day = date.day.toString().padLeft(2, '0');
    return '${date.year}/$month/$day';
  }

  String _formatAmount(int amount) {
    return amount.toString().replaceAllMapped(
      RegExp(r'\B(?=(\d{3})+(?!\d))'),
      (match) => ',',
    );
  }
}
