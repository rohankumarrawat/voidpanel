import 'package:flutter/material.dart';

class EventItem {
  final String id;
  final String title;
  final String location;
  final String startTime;
  final String endTime;
  final Color indicatorColor;
  final DateTime date;
  final String meetingUrl;
  final String meetingType;
  final String notes;
  final int reminderMinutes;
  final List<String> attendees;
  final String sourceEmailId;

  EventItem({
    required this.id,
    required this.title,
    required this.location,
    required this.startTime,
    required this.endTime,
    required this.indicatorColor,
    required this.date,
    this.meetingUrl = '',
    this.meetingType = 'video',
    this.notes = '',
    this.reminderMinutes = 15,
    this.attendees = const [],
    this.sourceEmailId = '',
  });

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'location': location,
      'startTime': startTime,
      'endTime': endTime,
      'indicatorColor': indicatorColor.toARGB32(),
      'date': date.toIso8601String(),
      'meeting_url': meetingUrl,
      'meeting_type': meetingType,
      'notes': notes,
      'reminder_minutes': reminderMinutes,
      'attendees': attendees,
      'source_email_id': sourceEmailId,
    };
  }

  factory EventItem.fromJson(Map<String, dynamic> json) {
    DateTime parsedDate = DateTime.now();
    if (json['start_time'] != null && json['start_time'].toString().isNotEmpty) {
      parsedDate = DateTime.tryParse(json['start_time']) ?? DateTime.now();
    } else if (json['date'] != null && json['date'].toString().isNotEmpty) {
      parsedDate = DateTime.tryParse(json['date']) ?? DateTime.now();
    }

    final meetingTypeStr = json['meeting_type'] ?? 'video';
    Color color = const Color(0xFF4F46E5);
    if (meetingTypeStr == 'call') color = const Color(0xFF10B981);
    if (meetingTypeStr == 'in_person') color = const Color(0xFFFF7A00);

    return EventItem(
      id: '${json['id'] ?? ''}',
      title: json['title'] ?? 'Calendar Event',
      location: json['location'] ?? (json['meeting_type'] == 'video' ? 'VoidMeet Room' : (json['location'] ?? 'Calendar')),
      startTime: json['time_str'] ?? json['startTime'] ?? '10:00 AM',
      endTime: json['end_time_str'] ?? json['endTime'] ?? '11:00 AM',
      indicatorColor: json['indicatorColor'] != null
          ? Color(json['indicatorColor'] is int ? json['indicatorColor'] : int.tryParse('${json['indicatorColor']}') ?? 0xFF4F46E5)
          : color,
      date: parsedDate,
      meetingUrl: json['meeting_url'] ?? '',
      meetingType: meetingTypeStr,
      notes: json['notes'] ?? '',
      reminderMinutes: json['reminder_minutes'] is int ? json['reminder_minutes'] : int.tryParse('${json['reminder_minutes']}') ?? 15,
      attendees: json['attendees'] is List ? List<String>.from(json['attendees']) : [],
      sourceEmailId: json['source_email_id'] ?? '',
    );
  }

  static List<EventItem> sampleEvents() {
    return [];
  }
}
