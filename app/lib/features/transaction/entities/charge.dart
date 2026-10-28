/// 支払い方法（→ docs/adr/0011）
enum PaymentPlan {
  lump('1回払い'),
  skip('スキップ払い'),
  installment('分割払い'),
  revolving('リボ払い');

  const PaymentPlan(this.label);

  final String label;

  static PaymentPlan fromJson(String value) => PaymentPlan.values.byName(value);
}

/// 支出の1回分の引き落とし。1回払いでも、支払日に金額の全部を払う1回分がある
class Charge {
  int seq;
  DateTime paidDate;
  int principal;
  int fee;
  int amount;
  bool feeEdited;

  Charge({
    required this.seq,
    required this.paidDate,
    required this.principal,
    required this.fee,
    required this.amount,
    required this.feeEdited,
  });

  factory Charge.fromJson(Map<String, dynamic> json) {
    return Charge(
      seq: json['seq'] as int,
      paidDate: DateTime.parse(json['paid_date'] as String),
      principal: json['principal'] as int,
      fee: json['fee'] as int,
      amount: json['amount'] as int,
      feeEdited: json['fee_edited'] as bool,
    );
  }
}

/// リボ払いの、ある支払い手段のひと月分の引き落とし（リボにした支出の全部を合わせた額）
class RevolvingMonth {
  String month;
  DateTime paidDate;
  int principal;
  int fee;
  int amount;
  bool feeEdited;

  /// 引き落としのあとに残る元金
  int balance;

  RevolvingMonth({
    required this.month,
    required this.paidDate,
    required this.principal,
    required this.fee,
    required this.amount,
    required this.feeEdited,
    required this.balance,
  });

  factory RevolvingMonth.fromJson(Map<String, dynamic> json) {
    return RevolvingMonth(
      month: json['month'] as String,
      paidDate: DateTime.parse(json['paid_date'] as String),
      principal: json['principal'] as int,
      fee: json['fee'] as int,
      amount: json['amount'] as int,
      feeEdited: json['fee_edited'] as bool,
      balance: json['balance'] as int,
    );
  }
}
