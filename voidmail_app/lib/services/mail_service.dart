import '../models/email_item.dart';

class MailService {
  /// Return empty list by default - no fake mock data
  static List<EmailItem> generateInitialEmails(String userEmail) {
    return [];
  }
}
