class ImportFailure {
  String messageId;
  String sender;
  String subject;
  String reason;
  DateTime failedAt;

  ImportFailure({
    required this.messageId,
    required this.sender,
    this.subject = '',
    required this.reason,
    required this.failedAt,
  });

  factory ImportFailure.fromJson(Map<String, dynamic> json) {
    return ImportFailure(
      messageId: json['message_id'] as String,
      sender: json['sender'] as String,
      subject: json['subject'] as String,
      reason: json['reason'] as String,
      failedAt: DateTime.parse(json['failed_at'] as String),
    );
  }
}
