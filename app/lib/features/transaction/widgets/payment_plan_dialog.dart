import 'package:flutter/material.dart';
import 'package:tsukena/features/transaction/entities/charge.dart';
import 'package:tsukena/features/transaction/entities/transaction.dart';
import 'package:tsukena/features/transaction/repositories/transaction_repository.dart';

/// 支出の支払い方法（1回払い・スキップ・分割・リボ払い）を変え、引き落としの予定を見るダイアログ（→ docs/adr/0011）。
///
/// 予定の額はカード会社の式で計算する。日割りや休日のずれで明細と違う回は、押して引き落とし額を直す。
/// 直した額は手数料で合わせる（元金は変えない）。閉じるときに、何か変えたら変えた後の支出を返す（変えなければ null）
class PaymentPlanDialog extends StatefulWidget {
  const PaymentPlanDialog({super.key, required this.transaction});

  final Transaction transaction;

  @override
  State<PaymentPlanDialog> createState() => _PaymentPlanDialogState();
}

// カード会社（JCB）で選べる範囲。サーバーも同じ範囲で受け付ける
const _skipMonths = [1, 2, 3, 4, 5, 6];
final _installmentCounts = [for (var i = 3; i <= 60; i++) i];

class _PaymentPlanDialogState extends State<PaymentPlanDialog> {
  late Transaction _transaction = widget.transaction;
  late PaymentPlan _plan = _transaction.paymentPlan;
  late int _skip = _transaction.paymentPlan == PaymentPlan.skip
      ? _transaction.planCount!
      : _skipMonths.first;
  late int _count = _transaction.paymentPlan == PaymentPlan.installment
      ? _transaction.planCount!
      : _installmentCounts.first;
  Future<List<RevolvingMonth>>? _revolving;
  bool _saving = false;
  bool _changed = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    if (_transaction.paymentPlan == PaymentPlan.revolving) {
      _revolving = _fetchRevolving();
    }
  }

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final t = _transaction;

    return AlertDialog(
      title: const Text('支払い方法'),
      content: SizedBox(
        width: 400,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '${t.merchant.isEmpty ? '(店名無し)' : t.merchant} ¥${_formatAmount(t.amount)}\n'
                '${t.paymentMethod}・1回払いなら ${_formatDate(t.paidDate)} に引き落とし',
                style: textTheme.bodySmall,
              ),
              const SizedBox(height: 16),
              DropdownButtonFormField<PaymentPlan>(
                decoration: const InputDecoration(labelText: '支払い方法'),
                initialValue: _plan,
                items: [
                  for (final plan in PaymentPlan.values)
                    DropdownMenuItem(value: plan, child: Text(plan.label)),
                ],
                onChanged: _saving
                    ? null
                    : (value) => setState(() => _plan = value!),
              ),
              if (_plan == PaymentPlan.skip) ...[
                const SizedBox(height: 16),
                DropdownButtonFormField<int>(
                  decoration: const InputDecoration(labelText: '支払い月'),
                  initialValue: _skip,
                  items: [
                    for (final months in _skipMonths)
                      DropdownMenuItem(
                        value: months,
                        child: Text('$monthsか月後に払う'),
                      ),
                  ],
                  onChanged: (value) => setState(() => _skip = value!),
                ),
              ],
              if (_plan == PaymentPlan.installment) ...[
                const SizedBox(height: 16),
                DropdownButtonFormField<int>(
                  decoration: const InputDecoration(labelText: '回数'),
                  initialValue: _count,
                  items: [
                    for (final count in _installmentCounts)
                      DropdownMenuItem(value: count, child: Text('$count回')),
                  ],
                  onChanged: (value) => setState(() => _count = value!),
                ),
              ],
              if (_plan == PaymentPlan.revolving) ...[
                const SizedBox(height: 8),
                Text(
                  'リボ払いは、同じカードでリボにした支出をまとめて、毎月決まった元金と残高の手数料を払います',
                  style: textTheme.bodySmall,
                ),
              ],
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerRight,
                child: FilledButton(
                  onPressed: _saving || !_isDirty ? null : _changePlan,
                  child: const Text('この支払い方法にする'),
                ),
              ),
              if (_error case final error?) ...[
                const SizedBox(height: 8),
                Text(
                  error,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ],
              if (t.paymentPlan != PaymentPlan.lump) ...[
                const Divider(height: 32),
                Text(
                  t.paymentPlan == PaymentPlan.revolving
                      ? '${t.paymentMethod}のリボ払い全体の引き落とし'
                      : '引き落としの予定',
                  style: textTheme.titleSmall,
                ),
                const SizedBox(height: 4),
                Text(
                  'カードの明細と額が違う回は、押して直してください（差は手数料で合わせます）',
                  style: textTheme.bodySmall,
                ),
                if (t.paymentPlan == PaymentPlan.revolving)
                  _buildRevolving()
                else
                  for (final charge in t.charges)
                    _ChargeTile(
                      label: '${charge.seq}回目 ${_formatDate(charge.paidDate)}',
                      amount: charge.amount,
                      principal: charge.principal,
                      fee: charge.fee,
                      edited: charge.feeEdited,
                      onTap: _saving ? null : () => _editCharge(charge),
                    ),
              ],
            ],
          ),
        ),
      ),
      actions: [
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            TextButton(
              onPressed: () =>
                  Navigator.of(context).pop(_changed ? _transaction : null),
              child: const Text('閉じる'),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildRevolving() {
    return FutureBuilder<List<RevolvingMonth>>(
      future: _revolving,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Padding(
            padding: EdgeInsets.all(16),
            child: Center(child: CircularProgressIndicator()),
          );
        }
        if (snapshot.hasError) {
          return const Padding(
            padding: EdgeInsets.all(16),
            child: Text('リボ払いの予定の取得に失敗しました'),
          );
        }
        return Column(
          children: [
            for (final month in snapshot.requireData)
              _ChargeTile(
                label: _formatDate(month.paidDate),
                amount: month.amount,
                principal: month.principal,
                fee: month.fee,
                edited: month.feeEdited,
                note: '残り ¥${_formatAmount(month.balance)}',
                onTap: _saving ? null : () => _editRevolving(month),
              ),
          ],
        );
      },
    );
  }

  bool get _isDirty {
    final t = _transaction;
    if (_plan != t.paymentPlan) return true;
    return switch (_plan) {
      PaymentPlan.skip => _skip != t.planCount,
      PaymentPlan.installment => _count != t.planCount,
      _ => false,
    };
  }

  Future<void> _changePlan() async {
    // 作り直すと、手で直した手数料は消える。直したものがあるときだけ確かめる
    if (_transaction.charges.any((c) => c.feeEdited) &&
        !await _confirm('直した引き落とし額は計算した額に戻ります。変えますか?')) {
      return;
    }
    await _run(() async {
      final updated = await TransactionService().putPaymentPlan(
        _transaction.id,
        _plan,
        count: switch (_plan) {
          PaymentPlan.skip => _skip,
          PaymentPlan.installment => _count,
          _ => null,
        },
      );
      _transaction = updated;
      _revolving = updated.paymentPlan == PaymentPlan.revolving
          ? _fetchRevolving()
          : null;
    }, failure: '支払い方法の変更に失敗しました');
  }

  Future<void> _editCharge(Charge charge) async {
    final edit = await showDialog<_FeeEdit>(
      context: context,
      builder: (_) => _ChargeAmountDialog(
        principal: charge.principal,
        amount: charge.amount,
        edited: charge.feeEdited,
      ),
    );
    if (edit == null) return;
    await _run(() async {
      _transaction = await TransactionService().putChargeFee(
        _transaction.id,
        charge.seq,
        edit.fee,
      );
    }, failure: '引き落とし額の修正に失敗しました');
  }

  Future<void> _editRevolving(RevolvingMonth month) async {
    final edit = await showDialog<_FeeEdit>(
      context: context,
      builder: (_) => _ChargeAmountDialog(
        principal: month.principal,
        amount: month.amount,
        edited: month.feeEdited,
      ),
    );
    if (edit == null) return;
    await _run(() async {
      final months = await TransactionService().putRevolvingFee(
        _transaction.paymentMethod,
        month.month,
        edit.fee,
      );
      _revolving = Future.value(months);
    }, failure: '引き落とし額の修正に失敗しました');
  }

  Future<void> _run(
    Future<void> Function() action, {
    required String failure,
  }) async {
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await action();
      _changed = true;
    } on PaymentPlanNotAvailable {
      _error = '${_transaction.paymentMethod}では、この支払い方法にできません';
    } catch (_) {
      _error = failure;
    }
    if (!mounted) return;
    setState(() => _saving = false);
  }

  Future<List<RevolvingMonth>> _fetchRevolving() =>
      TransactionService().getRevolving(_transaction.paymentMethod);

  Future<bool> _confirm(String message) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(message),
        actions: [
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              TextButton(
                onPressed: () => Navigator.of(context).pop(true),
                child: const Text('変える'),
              ),
              TextButton(
                onPressed: () => Navigator.of(context).pop(false),
                child: const Text('キャンセル'),
              ),
            ],
          ),
        ],
      ),
    );
    return confirmed == true;
  }
}

class _ChargeTile extends StatelessWidget {
  const _ChargeTile({
    required this.label,
    required this.amount,
    required this.principal,
    required this.fee,
    required this.edited,
    this.note,
    this.onTap,
  });

  final String label;
  final int amount;
  final int principal;
  final int fee;
  final bool edited;
  final String? note;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final detail =
        '元金 ¥${_formatAmount(principal)} + 手数料 ¥${_formatAmount(fee)}';
    return ListTile(
      dense: true,
      contentPadding: EdgeInsets.zero,
      onTap: onTap,
      title: Text(label),
      subtitle: Text([detail, ?note].join('・')),
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          // 手で直した回は、計算した額ではないと分かるようにする
          if (edited) const Icon(Icons.edit, size: 16),
          const SizedBox(width: 4),
          Text(
            '¥${_formatAmount(amount)}',
            style: Theme.of(context).textTheme.bodyLarge,
          ),
        ],
      ),
    );
  }
}

/// 引き落とし額の直し方。fee が null なら計算した額に戻す
class _FeeEdit {
  const _FeeEdit(this.fee);

  final int? fee;
}

/// 1回分の引き落とし額を、明細の額に合わせて直すダイアログ。元金は変えず、差を手数料にする
class _ChargeAmountDialog extends StatefulWidget {
  const _ChargeAmountDialog({
    required this.principal,
    required this.amount,
    required this.edited,
  });

  final int principal;
  final int amount;
  final bool edited;

  @override
  State<_ChargeAmountDialog> createState() => _ChargeAmountDialogState();
}

class _ChargeAmountDialogState extends State<_ChargeAmountDialog> {
  late String _amountText = widget.amount.toString();
  String? _error;

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('引き落とし額を直す'),
      content: SizedBox(
        width: 360,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextFormField(
              decoration: const InputDecoration(
                labelText: '明細の引き落とし額',
                suffixText: '円',
              ),
              keyboardType: TextInputType.number,
              autofocus: true,
              initialValue: _amountText,
              onChanged: (value) => _amountText = value,
            ),
            const SizedBox(height: 8),
            Text(
              '元金 ¥${_formatAmount(widget.principal)} は変えず、差を手数料にします',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            if (_error case final error?) ...[
              const SizedBox(height: 8),
              Text(
                error,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ],
          ],
        ),
      ),
      actions: [
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            TextButton(onPressed: _save, child: const Text('保存')),
            if (widget.edited)
              TextButton(
                onPressed: () =>
                    Navigator.of(context).pop(const _FeeEdit(null)),
                child: const Text('計算に戻す'),
              ),
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('キャンセル'),
            ),
          ],
        ),
      ],
    );
  }

  void _save() {
    final amount = int.tryParse(_amountText);
    if (amount == null || amount < widget.principal) {
      setState(
        () => _error = '元金 ¥${_formatAmount(widget.principal)} 以上の整数で入力してください',
      );
      return;
    }
    Navigator.of(context).pop(_FeeEdit(amount - widget.principal));
  }
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
