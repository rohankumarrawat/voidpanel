class TextSnippet {
  final String shortcut;
  final String title;
  final String content;

  const TextSnippet({
    required this.shortcut,
    required this.title,
    required this.content,
  });

  factory TextSnippet.fromJson(Map<String, dynamic> json) {
    return TextSnippet(
      shortcut: json['shortcut'] ?? '',
      title: json['title'] ?? '',
      content: json['content'] ?? '',
    );
  }

  Map<String, dynamic> toJson() => {
    'shortcut': shortcut,
    'title': title,
    'content': content,
  };
}
