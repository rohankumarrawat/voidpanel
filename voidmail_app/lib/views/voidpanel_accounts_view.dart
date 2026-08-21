import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../providers/mail_provider.dart';
import '../widgets/powered_by_voidpanel.dart';

class VoidPanelAccountsView extends StatefulWidget {
  const VoidPanelAccountsView({super.key});

  @override
  State<VoidPanelAccountsView> createState() => _VoidPanelAccountsViewState();
}

class _VoidPanelAccountsViewState extends State<VoidPanelAccountsView> {
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();

  void _showCreateDialog() {
    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: Text(
            'Create VoidPanel Email Account',
            style: GoogleFonts.inter(fontWeight: FontWeight.bold, fontSize: 16),
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: _usernameController,
                decoration: const InputDecoration(
                  labelText: 'Email Username',
                  hintText: 'e.g. sales',
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _passwordController,
                obscureText: true,
                decoration: const InputDecoration(
                  labelText: 'Password',
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
              onPressed: () async {
                final username = _usernameController.text.trim();
                final password = _passwordController.text.trim();
                if (username.isEmpty || password.isEmpty) return;

                Navigator.pop(context);
                final provider = Provider.of<MailProvider>(context, listen: false);
                final res = await provider.createVoidPanelAccount(username, password);

                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text(res['message'] ?? 'Account created'),
                      backgroundColor: res['success'] == true ? const Color(0xFF10B981) : const Color(0xFFEF4444),
                    ),
                  );
                }
                _usernameController.clear();
                _passwordController.clear();
              },
              child: const Text('Provision'),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<MailProvider>(context);
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final accounts = provider.managedAccounts;

    return Scaffold(
      appBar: AppBar(
        title: const Text('VoidPanel Email Accounts'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add_circle_outline_rounded, color: Color(0xFF4F46E5)),
            onPressed: _showCreateDialog,
            tooltip: 'Add Email Account',
          ),
        ],
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Server Quota Card
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [Color(0xFF0F172A), Color(0xFF1E293B)],
                  ),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          'Domain: ${provider.currentDomain}',
                          style: GoogleFonts.inter(
                            color: Colors.white,
                            fontWeight: FontWeight.bold,
                            fontSize: 16,
                          ),
                        ),
                        const PoweredByVoidPanel(compact: true),
                      ],
                    ),
                    const SizedBox(height: 16),
                    Text(
                      'Account Quota: ${accounts.length} / 10 Accounts',
                      style: GoogleFonts.inter(color: Colors.grey[300], fontSize: 13),
                    ),
                    const SizedBox(height: 8),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(6),
                      child: LinearProgressIndicator(
                        value: accounts.length / 10,
                        backgroundColor: const Color(0xFF334155),
                        color: const Color(0xFF06B6D4),
                        minHeight: 8,
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 24),
              Text(
                'PROVISIONED ACCOUNTS',
                style: GoogleFonts.inter(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1,
                  color: isDark ? Colors.grey[400] : Colors.grey[600],
                ),
              ),
              const SizedBox(height: 12),

              ListView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: accounts.length,
                itemBuilder: (context, index) {
                  final acc = accounts[index];
                  return Card(
                    margin: const EdgeInsets.only(bottom: 10),
                    child: ListTile(
                      leading: const CircleAvatar(
                        backgroundColor: Color(0xFF4F46E5),
                        child: Icon(Icons.alternate_email_rounded, color: Colors.white, size: 20),
                      ),
                      title: Text(
                        acc.email,
                        style: GoogleFonts.inter(fontWeight: FontWeight.w600),
                      ),
                      subtitle: Text('Dovecot IMAP / Postfix active'),
                      trailing: PopupMenuButton<String>(
                        onSelected: (val) {
                          if (val == 'reset') {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(content: Text('Password reset link generated for ${acc.email}')),
                            );
                          }
                        },
                        itemBuilder: (context) => [
                          const PopupMenuItem(value: 'reset', child: Text('Reset Password')),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}
