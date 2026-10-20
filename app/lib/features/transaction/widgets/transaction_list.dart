import 'package:flutter/material.dart';
import 'package:tsukena/features/transaction/entities/category.dart';
import 'package:tsukena/features/transaction/entities/transaction.dart';

class TransactionList extends StatelessWidget {
  const TransactionList({
    super.key,
    required this.transactions,
    required this.categories,
    this.onTap,
  });

  final List<Transaction> transactions;
  final Map<int, Category> categories;
  final ValueChanged<Transaction>? onTap;

  @override
  Widget build(BuildContext context) {
    if (transactions.isEmpty) {
      return const Center(child: Text('取引がありません'));
    }

    final textTheme = Theme.of(context).textTheme;

    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 600),
        child: ListView.separated(
          padding: const EdgeInsets.symmetric(vertical: 8),
          itemCount: transactions.length,
          separatorBuilder: (context, index) => const Divider(height: 1),
          itemBuilder: (context, index) {
            final transaction = transactions[index];

            final categoryId = transaction.categoryId;
            final category = categoryId == null ? null : categories[categoryId];

            final time = transaction.occurredTime;
            final date = _formatDate(transaction.occurredDate);
            final datetime = time == null ? date : '$date ${_formatTime(time)}';

            return ListTile(
              onTap: onTap == null ? null : () => onTap!(transaction),
              leading: Text(
                category?.emoji ?? '❓',
                style: textTheme.headlineSmall,
              ),
              title: Text(
                transaction.merchant.isEmpty ? '(店名無し)' : transaction.merchant,
              ),
              // メモがあれば、何を買ったか分かるよう2行目に出す
              subtitle: Text(
                transaction.memo.isEmpty
                    ? '$datetime ・ ${transaction.paymentMethod}'
                    : '$datetime ・ ${transaction.paymentMethod}\n${transaction.memo}',
              ),
              trailing: Text(
                '¥${_formatAmount(transaction.amount)}',
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

  String _formatTime(TimeOfDay time) {
    final hour = time.hour.toString().padLeft(2, '0');
    final minute = time.minute.toString().padLeft(2, '0');
    return '$hour:$minute';
  }

  String _formatAmount(int amount) {
    return amount.toString().replaceAllMapped(
      RegExp(r'\B(?=(\d{3})+(?!\d))'),
      (match) => ',',
    );
  }
}
