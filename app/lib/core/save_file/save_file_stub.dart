/// Web 版以外では保存できない
Future<void> saveTextFile(String fileName, String content, String mimeType) {
  throw UnsupportedError('この環境ではファイルを保存できません');
}
