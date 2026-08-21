import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/event_item.dart';
import '../providers/mail_provider.dart';

class CalendarView extends StatefulWidget {
  const CalendarView({super.key});

  @override
  State<CalendarView> createState() => _CalendarViewState();
}

class _CalendarViewState extends State<CalendarView> {
  late DateTime _selectedDate;
  List<EventItem> _events = [];

  @override
  void initState() {
    super.initState();
    _selectedDate = DateTime.now();
    _loadEvents();
  }

  Future<void> _loadEvents() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final jsonString = prefs.getString('calendar_events');
      if (jsonString != null && jsonString.isNotEmpty) {
        final List<dynamic> decoded = jsonDecode(jsonString);
        setState(() {
          _events = decoded.map((item) => EventItem.fromJson(item)).toList();
        });
      }
    } catch (e) {
      debugPrint('[Calendar] Error loading events: $e');
    }
  }

  Future<void> _saveEvents() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final encoded = jsonEncode(_events.map((e) => e.toJson()).toList());
      await prefs.setString('calendar_events', encoded);
    } catch (e) {
      debugPrint('[Calendar] Error saving events: $e');
    }
  }

  void _deleteEvent(String id) {
    setState(() {
      _events.removeWhere((e) => e.id == id);
    });
    _saveEvents();
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Event deleted'),
        behavior: SnackBarBehavior.floating,
        duration: Duration(seconds: 2),
      ),
    );
  }

  void _showAddEventDialog() {
    final titleCtrl = TextEditingController();
    final timeCtrl = TextEditingController(text: '10:00 AM');

    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: Text('Add New Event', style: GoogleFonts.inter(fontWeight: FontWeight.bold)),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: titleCtrl,
                decoration: const InputDecoration(
                  labelText: 'Event Title',
                  prefixIcon: Icon(Icons.event_outlined),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: timeCtrl,
                decoration: const InputDecoration(
                  labelText: 'Start Time',
                  prefixIcon: Icon(Icons.access_time_rounded),
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () {
                final title = titleCtrl.text.trim();
                final time = timeCtrl.text.trim();
                if (title.isNotEmpty) {
                  setState(() {
                    _events.add(
                      EventItem(
                        id: 'event-${DateTime.now().millisecondsSinceEpoch}',
                        title: title,
                        location: 'Calendar Event',
                        startTime: time,
                        endTime: '11:00 AM',
                        indicatorColor: const Color(0xFF6C5CE7),
                        date: _selectedDate,
                      ),
                    );
                  });
                  _saveEvents();
                  Navigator.pop(context);
                }
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF6C5CE7),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              child: const Text('Save Event', style: TextStyle(color: Colors.white)),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final now = DateTime.now();
    final monthYearStr = DateFormat('MMMM yyyy').format(_selectedDate);

    // Filter events for selected date
    final dayEvents = _events.where((e) {
      return e.date.day == _selectedDate.day &&
          e.date.month == _selectedDate.month &&
          e.date.year == _selectedDate.year;
    }).toList();

    return Scaffold(
      backgroundColor: isDark ? const Color(0xFF0F0C20) : const Color(0xFFF9FAFD),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 1. Top Bar Header Title & Quick Actions matching Design Image
              Row(
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Calendar',
                        style: GoogleFonts.outfit(
                          fontSize: 26,
                          fontWeight: FontWeight.bold,
                          color: isDark ? Colors.white : const Color(0xFF0F172A),
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        'Friday, August 7, 2026',
                        style: GoogleFonts.inter(
                          fontSize: 13,
                          color: isDark ? Colors.grey[400] : const Color(0xFF64748B),
                        ),
                      ),
                    ],
                  ),
                  const Spacer(),
                  // Search Button
                  Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: isDark ? const Color(0xFF1B1638) : Colors.white,
                      shape: BoxShape.circle,
                      border: Border.all(color: const Color(0xFFE2E8F0)),
                    ),
                    child: const Icon(Icons.search_rounded, color: Color(0xFF475569), size: 20),
                  ),
                  const SizedBox(width: 10),
                  // Plus Add Event Button
                  GestureDetector(
                    onTap: _showAddEventDialog,
                    child: Container(
                      width: 40,
                      height: 40,
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                          colors: [Color(0xFF6366F1), Color(0xFF4F46E5)],
                        ),
                        shape: BoxShape.circle,
                        boxShadow: [
                          BoxShadow(
                            color: const Color(0xFF6366F1).withOpacity(0.35),
                            blurRadius: 10,
                            offset: const Offset(0, 4),
                          ),
                        ],
                      ),
                      child: const Icon(Icons.add_rounded, color: Colors.white, size: 22),
                    ),
                  ),
                ],
              ),

              const SizedBox(height: 20),

              // 2. Date Selector Container Card matching Design Image
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: isDark ? const Color(0xFF1B1638) : Colors.white,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: isDark ? const Color(0xFF2C2554) : const Color(0xFFEEF2FF)),
                  boxShadow: [
                    BoxShadow(color: Colors.black.withOpacity(0.02), blurRadius: 10, offset: const Offset(0, 2)),
                  ],
                ),
                child: Column(
                  children: [
                    // Header: August 2026 dropdown, Today, < >
                    Row(
                      children: [
                        Text('August 2026', style: GoogleFonts.inter(fontWeight: FontWeight.bold, fontSize: 15)),
                        const Icon(Icons.keyboard_arrow_down_rounded, size: 18, color: Color(0xFF6366F1)),
                        const Spacer(),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                          decoration: BoxDecoration(
                            color: const Color(0xFFEEF2FF),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Text('Today', style: GoogleFonts.inter(fontSize: 11, fontWeight: FontWeight.bold, color: const Color(0xFF4338CA))),
                        ),
                        const SizedBox(width: 8),
                        const Icon(Icons.chevron_left_rounded, size: 20, color: Color(0xFF94A3B8)),
                        const SizedBox(width: 4),
                        const Icon(Icons.chevron_right_rounded, size: 20, color: Color(0xFF94A3B8)),
                      ],
                    ),
                    const SizedBox(height: 16),

                    // Date Strip matching Screenshot (TUE 4, WED 5, THU 6, FRI 7 active, SAT 8, SUN 9 red, MON 10)
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceAround,
                      children: List.generate(7, (i) {
                        final day = now.add(Duration(days: i - 3));
                        final isSelected = day.day == _selectedDate.day &&
                            day.month == _selectedDate.month &&
                            day.year == _selectedDate.year;
                        final dayName = DateFormat('EEE').format(day).toUpperCase();
                        final isSunday = day.weekday == DateTime.sunday;

                        return GestureDetector(
                          onTap: () => setState(() => _selectedDate = day),
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                            decoration: BoxDecoration(
                              color: isSelected ? const Color(0xFF6366F1) : Colors.transparent,
                              borderRadius: BorderRadius.circular(16),
                            ),
                            child: Column(
                              children: [
                                Text(
                                  dayName,
                                  style: GoogleFonts.inter(
                                    fontSize: 10,
                                    fontWeight: FontWeight.bold,
                                    color: isSelected
                                        ? Colors.white
                                        : (isSunday ? Colors.redAccent : (isDark ? Colors.grey[400] : const Color(0xFF64748B))),
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  '${day.day}',
                                  style: GoogleFonts.inter(
                                    fontSize: 14,
                                    fontWeight: FontWeight.bold,
                                    color: isSelected
                                        ? Colors.white
                                        : (isSunday ? Colors.redAccent : (isDark ? Colors.white : const Color(0xFF0F172A))),
                                  ),
                                ),
                                if (isSelected) ...[
                                  const SizedBox(height: 2),
                                  Container(
                                    width: 4,
                                    height: 4,
                                    decoration: const BoxDecoration(color: Colors.white, shape: BoxShape.circle),
                                  ),
                                ],
                              ],
                            ),
                          ),
                        );
                      }),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 24),

              // 3. 3D Hero Graphic Empty State or Events List matching Mockup
              if (dayEvents.isEmpty) ...[
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(vertical: 28, horizontal: 20),
                  child: Column(
                    children: [
                      // 3D Style Calendar Graphic Box matching Image 2
                      Container(
                        width: 110,
                        height: 110,
                        decoration: BoxDecoration(
                          color: const Color(0xFFEEF2FF),
                          borderRadius: BorderRadius.circular(32),
                          boxShadow: [
                            BoxShadow(
                              color: const Color(0xFF6366F1).withOpacity(0.15),
                              blurRadius: 20,
                              offset: const Offset(0, 6),
                            ),
                          ],
                        ),
                        child: Stack(
                          alignment: Alignment.center,
                          children: [
                            const Icon(Icons.calendar_month_rounded, size: 54, color: Color(0xFF6366F1)),
                            Positioned(
                              right: 22,
                              bottom: 22,
                              child: Container(
                                padding: const EdgeInsets.all(4),
                                decoration: const BoxDecoration(color: Color(0xFF10B981), shape: BoxShape.circle),
                                child: const Icon(Icons.check, size: 12, color: Colors.white),
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 20),

                      Text(
                        'No events scheduled',
                        style: GoogleFonts.outfit(
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                          color: isDark ? Colors.white : const Color(0xFF0F172A),
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'Tap + to create a new event for\n${DateFormat('EEEE, MMMM d, yyyy').format(_selectedDate)}',
                        textAlign: TextAlign.center,
                        style: GoogleFonts.inter(
                          fontSize: 13,
                          color: isDark ? Colors.grey[400] : const Color(0xFF64748B),
                        ),
                      ),
                      const SizedBox(height: 20),

                      // Add Event Button Pill matching Mockup
                      ElevatedButton.icon(
                        onPressed: _showAddEventDialog,
                        icon: const Icon(Icons.add_rounded, size: 18, color: Colors.white),
                        label: Text('Add Event', style: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.white)),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF6366F1),
                          padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 14),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                          elevation: 4,
                        ),
                      ),
                    ],
                  ),
                ),
              ] else ...[
                // List of Events
                ListView.builder(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  itemCount: dayEvents.length,
                  itemBuilder: (context, index) {
                    final ev = dayEvents[index];
                    return Container(
                      margin: const EdgeInsets.only(bottom: 12),
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: isDark ? const Color(0xFF1B1638) : Colors.white,
                        borderRadius: BorderRadius.circular(18),
                        border: Border.all(color: isDark ? const Color(0xFF2C2554) : const Color(0xFFEEF2FF)),
                        boxShadow: [
                          BoxShadow(color: Colors.black.withOpacity(0.02), blurRadius: 8, offset: const Offset(0, 2)),
                        ],
                      ),
                      child: Row(
                        children: [
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(ev.startTime, style: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.bold)),
                              const SizedBox(height: 2),
                              Text(ev.endTime, style: GoogleFonts.inter(fontSize: 11, color: const Color(0xFF64748B))),
                            ],
                          ),
                          const SizedBox(width: 16),
                          Container(width: 4, height: 36, decoration: BoxDecoration(color: ev.indicatorColor, borderRadius: BorderRadius.circular(2))),
                          const SizedBox(width: 16),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(ev.title, style: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.bold)),
                                const SizedBox(height: 2),
                                Text(ev.location, style: GoogleFonts.inter(fontSize: 11, color: const Color(0xFF64748B))),
                              ],
                            ),
                          ),
                          IconButton(
                            icon: const Icon(Icons.delete_outline_rounded, size: 20, color: Colors.redAccent),
                            onPressed: () => _deleteEvent(ev.id),
                          ),
                        ],
                      ),
                    );
                  },
                ),
              ],

              const SizedBox(height: 24),

              // 4. AI Suggestions Card matching Mock-up Bottom Section
              if (Provider.of<MailProvider>(context, listen: false).aiEnabled)
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: isDark ? const Color(0xFF1B1638) : Colors.white,
                  borderRadius: BorderRadius.circular(22),
                  border: Border.all(color: isDark ? const Color(0xFF2C2554) : const Color(0xFFEEF2FF)),
                  boxShadow: [
                    BoxShadow(color: Colors.black.withOpacity(0.02), blurRadius: 10, offset: const Offset(0, 2)),
                  ],
                ),
                child: Column(
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.auto_awesome_rounded, size: 18, color: Color(0xFF6366F1)),
                        const SizedBox(width: 6),
                        Text(
                          'AI Suggestions',
                          style: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.bold, color: const Color(0xFF4338CA)),
                        ),
                        const Spacer(),
                        Text('See all >', style: GoogleFonts.inter(fontSize: 12, color: const Color(0xFF64748B))),
                      ],
                    ),
                    const SizedBox(height: 14),

                    // AI Suggestion Item Row matching Screenshot
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: isDark ? const Color(0xFF16122E) : const Color(0xFFF8F9FE),
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.all(10),
                            decoration: BoxDecoration(
                              color: const Color(0xFF6366F1).withOpacity(0.12),
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: const Icon(Icons.event_note_rounded, color: Color(0xFF6366F1), size: 20),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text('Team Stand-up Meeting', style: GoogleFonts.inter(fontWeight: FontWeight.bold, fontSize: 13)),
                                Text('Every weekday • 10:00 AM', style: GoogleFonts.inter(fontSize: 11, color: const Color(0xFF64748B))),
                              ],
                            ),
                          ),
                          OutlinedButton(
                            onPressed: () {
                              setState(() {
                                _events.add(
                                  EventItem(
                                    id: 'suggestion-${DateTime.now().millisecondsSinceEpoch}',
                                    title: 'Team Stand-up Meeting',
                                    location: 'Google Meet',
                                    startTime: '10:00 AM',
                                    endTime: '10:30 AM',
                                    indicatorColor: const Color(0xFF6366F1),
                                    date: _selectedDate,
                                  ),
                                );
                              });
                              _saveEvents();
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(content: Text('Added Team Stand-up Meeting!'), backgroundColor: Color(0xFF10B981)),
                              );
                            },
                            style: OutlinedButton.styleFrom(
                              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                              side: const BorderSide(color: Color(0xFFC7D2FE)),
                            ),
                            child: Text('Add', style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.bold, color: const Color(0xFF6366F1))),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 20),
            ],
          ),
        ),
      ),
    );
  }
}
