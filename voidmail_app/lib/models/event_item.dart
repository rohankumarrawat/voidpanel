import 'package:flutter/material.dart';

class EventItem {
  final String id;
  final String title;
  final String location;
  final String startTime;
  final String endTime;
  final Color indicatorColor;
  final DateTime date;

  EventItem({
    required this.id,
    required this.title,
    required this.location,
    required this.startTime,
    required this.endTime,
    required this.indicatorColor,
    required this.date,
  });

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'location': location,
      'startTime': startTime,
      'endTime': endTime,
      'indicatorColor': indicatorColor.value,
      'date': date.toIso8601String(),
    };
  }

  factory EventItem.fromJson(Map<String, dynamic> json) {
    return EventItem(
      id: json['id'] ?? '',
      title: json['title'] ?? '',
      location: json['location'] ?? 'Calendar Event',
      startTime: json['startTime'] ?? '10:00 AM',
      endTime: json['endTime'] ?? '11:00 AM',
      indicatorColor: Color(json['indicatorColor'] ?? 0xFF6C5CE7),
      date: DateTime.tryParse(json['date'] ?? '') ?? DateTime.now(),
    );
  }

  static List<EventItem> sampleEvents() {
    return [];
  }
}
