class Income {
  int id;
  DateTime receivedDate;
  int amount;
  String memo;
  DateTime createdAt;
  DateTime updatedAt;

  Income({
    this.id = 0,
    required this.receivedDate,
    required this.amount,
    this.memo = '',
    required this.createdAt,
    required this.updatedAt,
  });

  factory Income.fromJson(Map<String, dynamic> json) {
    return Income(
      id: json['id'] as int,
      receivedDate: DateTime.parse(json['received_date'] as String),
      amount: json['amount'] as int,
      memo: json['memo'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
    );
  }
}
