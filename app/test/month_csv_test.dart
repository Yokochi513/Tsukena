import 'package:flutter_test/flutter_test.dart';
import 'package:tsukena/features/income/entities/income.dart';
import 'package:tsukena/features/month_export/month_csv.dart';
import 'package:tsukena/features/transaction/entities/category.dart';
import 'package:tsukena/features/transaction/entities/charge.dart';
import 'package:tsukena/features/transaction/entities/transaction.dart';

Transaction _transaction({
  required int id,
  required DateTime paidDate,
  required int amount,
  String merchant = '',
  String memo = '',
  int? categoryId,
  TransactionStatus status = TransactionStatus.confirmed,
  PaymentPlan plan = PaymentPlan.lump,
  int? planCount,
  List<Charge>? charges,
}) {
  final now = DateTime(2026, 10, 1);
  return Transaction(
    id: id,
    occurredDate: DateTime(2026, 9, 5),
    paidDate: paidDate,
    amount: amount,
    merchant: merchant,
    memo: memo,
    categoryId: categoryId,
    status: status,
    paymentMethod: 'JCB',
    source: TransactionSource.gmail,
    createdAt: now,
    updatedAt: now,
    paymentPlan: plan,
    planCount: planCount,
    charges:
        charges ??
        [
          Charge(
            seq: 1,
            paidDate: paidDate,
            principal: amount,
            fee: 0,
            amount: amount,
            feeEdited: false,
          ),
        ],
  );
}

void main() {
  final month = DateTime(2026, 10);
  final categories = [Category(id: 1, name: '食費', emoji: '🍚', sortOrder: 1)];

  test('支出と収入を日付の順に並べ、BOM と CRLF で書く', () {
    final csv = buildMonthCsv(
      month: month,
      transactions: [
        _transaction(
          id: 1,
          paidDate: DateTime(2026, 10, 10),
          amount: 450,
          merchant: 'コーヒー',
          categoryId: 1,
        ),
      ],
      incomes: [
        Income(
          receivedDate: DateTime(2026, 10, 1),
          amount: 300000,
          memo: '給与',
          createdAt: month,
          updatedAt: month,
        ),
      ],
      categories: categories,
    );

    expect(csv.startsWith('﻿'), isTrue);
    final lines = csv.substring(1).split('\r\n');
    expect(lines, [
      '種別,日付,利用日,店名,カテゴリ,金額,利用額,支払い方法,支払い手段,状態,メモ',
      '収入,2026-10-01,,,,300000,,,,,給与',
      '支出,2026-10-10,2026-09-05,コーヒー,食費,450,450,1回払い,JCB,,',
      '',
    ]);
  });

  test('分割払いは、その月の引き落とし日と額を出す', () {
    final csv = buildMonthCsv(
      month: month,
      transactions: [
        _transaction(
          id: 1,
          paidDate: DateTime(2026, 9, 10),
          amount: 30000,
          plan: PaymentPlan.installment,
          planCount: 3,
          charges: [
            for (final (seq, m) in [(1, 9), (2, 10), (3, 11)])
              Charge(
                seq: seq,
                paidDate: DateTime(2026, m, 10),
                principal: 10000,
                fee: 150,
                amount: 10150,
                feeEdited: false,
              ),
          ],
        ),
      ],
      incomes: [],
      categories: categories,
    );

    expect(
      csv.split('\r\n')[1],
      '支出,2026-10-10,2026-09-05,,,10150,30000,分割払い 2/3回,JCB,,',
    );
  });

  test('カンマ・引用符・改行を含む値は引用符で囲み、確認待ちを書く', () {
    final csv = buildMonthCsv(
      month: month,
      transactions: [
        _transaction(
          id: 1,
          paidDate: DateTime(2026, 10, 3),
          amount: 1280,
          merchant: 'A,B',
          memo: '1行目\n"2行目"',
          status: TransactionStatus.pending,
        ),
      ],
      incomes: [],
      categories: categories,
    );

    expect(
      csv.substring(csv.indexOf('\r\n') + 2),
      '支出,2026-10-03,2026-09-05,"A,B",,1280,1280,1回払い,JCB,確認待ち,'
      '"1行目\n""2行目"""\r\n',
    );
  });
}
