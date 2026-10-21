import 'package:flutter/material.dart';

class TransactionPendingBanner extends StatelessWidget {
  const TransactionPendingBanner({
    super.key,
    required this.count,
    required this.onTap,
  });

  final int count;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colorSchema = Theme.of(context).colorScheme;

    return Card(
      color: colorSchema.tertiaryContainer,
      margin: const EdgeInsets.fromLTRB(16, 8, 16, 0),
      child: ListTile(
        leading: const Icon(Icons.pending_actions),
        title: Text('確認待ちが $count件あります'),
        trailing: const Icon(Icons.chevron_right),
        onTap: onTap,
      ),
    );
  }
}
