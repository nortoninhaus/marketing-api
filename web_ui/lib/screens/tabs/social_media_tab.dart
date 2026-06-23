import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/providers.dart';
import '../../theme/app_theme.dart';

class SocialMediaTab extends ConsumerStatefulWidget {
  const SocialMediaTab({super.key});

  @override
  ConsumerState<SocialMediaTab> createState() => _SocialMediaTabState();
}

class _SocialMediaTabState extends ConsumerState<SocialMediaTab> {
  final TextEditingController _urlController = TextEditingController(text: 'https://tiktok.com/@viral_example/video/12345');
  final TextEditingController _promptController = TextEditingController(text: 'A clean cinematic shot of a marketer looking at high-performing graphs, hyperrealistic.');
  
  bool _analyzing = false;
  Map<String, dynamic>? _analysisResults;
  double _timelineValue = 0.0;
  
  bool _generating = false;
  Map<String, dynamic>? _generationResults;
  String _selectedModelA = 'veo_3';
  String _selectedModelB = 'sora_2';
  String _selectedAspectRatio = '9:16';

  List<dynamic> _tickets = [];
  List<dynamic> _alerts = [];
  bool _loadingTickets = false;
  bool _loadingAlerts = false;

  // Sub-tab Navigation
  int _subTabIndex = 0; // 0 = Inbox, 1 = Calendar & Creator, 2 = Listening & Brand Health
  Map<String, dynamic>? _activeTicket;

  // New state variables for Inbox
  final Map<String, String> _ticketAssignee = {};
  final Map<String, String> _ticketPriority = {};
  final Map<String, String> _ticketSentiment = {};
  final Map<String, String> _ticketCategory = {};
  final Map<String, List<String>> _ticketEscalationLogs = {};

  // New state variables for Publishing Hub
  int _publishingViewMode = 0; // 0 = Calendario Semanal, 1 = Flujo de Aprobación Kanban
  final List<Map<String, dynamic>> _approvalPosts = [
    {
      'id': 'post-1',
      'title': 'Lanzamiento de SOTA AI',
      'content': 'Estamos emocionados de presentar la nueva suite de marketing impulsada por IA. ¡Pruébala hoy!',
      'platform': 'instagram',
      'status': 'Borrador',
      'viral_time': '10:15 AM (ViralPost® Sugerido)',
      'image': 'https://assets.cdn.filesafe.space/7w7j6sfnicAwqdXG0sKP/media/6a18c4e6f58810f313b89b59.png'
    },
    {
      'id': 'post-2',
      'title': 'Estrategia de Presupuesto',
      'content': 'Aprende a distribuir tus recursos publicitarios eficientemente usando reglas automáticas.',
      'platform': 'tiktok',
      'status': 'Pendiente de Cliente',
      'viral_time': '02:30 PM (ViralPost® Sugerido)',
      'image': 'https://assets.cdn.filesafe.space/7w7j6sfnicAwqdXG0sKP/media/6a18c4e6f58810f313b89b59.png'
    },
    {
      'id': 'post-3',
      'title': 'Análisis de Retornos A/B',
      'content': 'Comparamos el rendimiento de Veo 3 frente a Sora 2 en formatos de vídeo móvil.',
      'platform': 'twitter',
      'status': 'Aprobado',
      'viral_time': '11:15 AM (ViralPost® Sugerido)',
      'image': 'https://assets.cdn.filesafe.space/7w7j6sfnicAwqdXG0sKP/media/6a18c4e6f58810f313b89b59.png'
    },
    {
      'id': 'post-4',
      'title': 'Caso de Éxito Inhaus',
      'content': 'Cómo una agencia duplicó sus conversiones en retail media usando la API de AdButler.',
      'platform': 'instagram',
      'status': 'Borrador',
      'viral_time': '09:00 AM (ViralPost® Sugerido)',
      'image': 'https://assets.cdn.filesafe.space/7w7j6sfnicAwqdXG0sKP/media/6a18c4e6f58810f313b89b59.png'
    },
  ];

  @override
  void initState() {
    super.initState();
    _loadSocialData();
  }

  Future<void> _loadSocialData() async {
    setState(() {
      _loadingTickets = true;
      _loadingAlerts = true;
    });
    try {
      final client = ref.read(apiClientProvider);
      final tickets = await client.getSocialTickets();
      final alerts = await client.getListeningAlerts();
      setState(() {
        _tickets = tickets;
        _alerts = alerts;
        for (var t in tickets) {
          final tid = t['id'] ?? '';
          _ticketPriority[tid] = t['sentiment'] == 'negative' ? 'high' : 'medium';
          _ticketSentiment[tid] = t['sentiment'] ?? 'neutral';
          _ticketAssignee[tid] = 'AgentIA';
          _ticketCategory[tid] = 'Soporte';
        }
        if (tickets.isNotEmpty) {
          _activeTicket = tickets.first;
        }
      });
    } catch (e) {
      debugPrint('Failed to load social data: $e');
    } finally {
      setState(() {
        _loadingTickets = false;
        _loadingAlerts = false;
      });
    }
  }

  void _escalateTicket(String service) {
    if (_activeTicket == null) return;
    final id = _activeTicket!['id'] ?? 'TKT-UNK';
    final user = _activeTicket!['user'] ?? '@usuario';
    final msg = _activeTicket!['message'] ?? '';
    final priority = _ticketPriority[id] ?? 'medium';
    final category = _ticketCategory[id] ?? 'Soporte';
    final assignee = _ticketAssignee[id] ?? 'AgentIA';
    final timestamp = DateTime.now().toIso8601String().substring(11, 19);

    String url = '';
    String payload = '';
    String response = '';
    String createdId = '';

    if (service == 'Zendesk') {
      url = 'POST https://inhaus.zendesk.com/api/v2/tickets.json';
      createdId = 'ZND-${100000 + DateTime.now().millisecond}';
      payload = '''{
  "ticket": {
    "subject": "Inbox Escalation: $user",
    "priority": "$priority",
    "tags": ["$category", "inhaus-api"],
    "comment": {
      "body": "Message: $msg\\n\\nEscalated by: $assignee"
    }
  }
}''';
      response = '''{
  "ticket": {
    "id": "$createdId",
    "status": "new",
    "subject": "Inbox Escalation: $user",
    "created_at": "${DateTime.now().toIso8601String()}"
  }
}''';
    } else {
      url = 'POST https://inhaus.my.salesforce.com/services/data/v58.0/sobjects/Case';
      createdId = '5008000000${1000 + DateTime.now().millisecond}abc';
      payload = '''{
  "Subject": "Social Case from $user",
  "Priority": "${priority.toUpperCase()}",
  "Description": "$msg",
  "Origin": "Social Inbox ($category)",
  "Owner": "$assignee"
}''';
      response = '''{
  "id": "$createdId",
  "success": true,
  "errors": []
}''';
    }

    setState(() {
      _ticketEscalationLogs.putIfAbsent(id, () => []).addAll([
        '[$timestamp] Initiating Sandbox escalation to $service...',
        '[$timestamp] ENDPOINT: $url',
        '[$timestamp] PAYLOAD:\\n$payload',
        '[$timestamp] STATUS: 201 Created',
        '[$timestamp] RESPONSE:\\n$response',
        '[$timestamp] SUCCESS: Ticket $createdId created in $service.',
      ]);
    });
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Escalado a $service exitosamente (ID: $createdId)')),
    );
  }

  Future<void> _analyzeVideo() async {
    setState(() {
      _analyzing = true;
      _analysisResults = null;
    });
    try {
      final client = ref.read(apiClientProvider);
      final res = await client.analyzeVideo(_urlController.text);
      setState(() {
        _analysisResults = res;
        _timelineValue = 0.0;
      });
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
    } finally {
      setState(() {
        _analyzing = false;
      });
    }
  }

  Future<void> _generateMedia() async {
    setState(() {
      _generating = true;
      _generationResults = null;
    });
    try {
      final client = ref.read(apiClientProvider);
      final res = await client.generateMedia(_promptController.text, _selectedModelA);
      setState(() {
        _generationResults = res;
      });
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
    } finally {
      setState(() {
        _generating = false;
      });
    }
  }

  Widget _buildSubTabBar() {
    return Container(
      margin: const EdgeInsets.only(bottom: 24),
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: AppTheme.surfaceColor,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white10),
      ),
      child: Row(
        children: [
          _buildSubTabButton(0, Icons.mail_outline, 'Smart Inbox'),
          _buildSubTabButton(1, Icons.calendar_month_outlined, 'Calendario & Creador'),
          _buildSubTabButton(2, Icons.analytics_outlined, 'Listening & Analytics'),
        ],
      ),
    );
  }

  Widget _buildSubTabButton(int index, IconData icon, String label) {
    final active = _subTabIndex == index;
    return Expanded(
      child: InkWell(
        onTap: () => setState(() => _subTabIndex = index),
        borderRadius: BorderRadius.circular(8),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 12),
          decoration: BoxDecoration(
            color: active ? AppTheme.secondaryColor.withOpacity(0.15) : Colors.transparent,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: active ? AppTheme.secondaryColor : Colors.transparent),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, color: active ? AppTheme.secondaryColor : AppTheme.mutedTextColor, size: 18),
              const SizedBox(width: 8),
              Text(
                label,
                style: TextStyle(
                  color: active ? AppTheme.primaryColor : AppTheme.mutedTextColor,
                  fontWeight: active ? FontWeight.bold : FontWeight.normal,
                  fontSize: 13,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // --- SUB TAB 0: SMART INBOX ---
  Widget _buildSmartInbox() {
    if (_loadingTickets) {
      return const Center(child: CircularProgressIndicator());
    }

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Tickets List (Left Pane)
        Expanded(
          flex: 4,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Conversaciones del Smart Inbox', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
              const SizedBox(height: 12),
              _tickets.isEmpty
                  ? const Card(child: Padding(padding: EdgeInsets.all(20), child: Text('No hay mensajes pendientes en el Inbox.')))
                  : ListView.builder(
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      itemCount: _tickets.length,
                      itemBuilder: (context, idx) {
                        final t = _tickets[idx];
                        final tid = t['id'] ?? '';
                        final isSelected = _activeTicket != null && _activeTicket!['id'] == t['id'];
                        
                        IconData platformIcon = Icons.link;
                        Color platformColor = AppTheme.secondaryColor;
                        if (t['platform'] == 'tiktok') {
                          platformIcon = Icons.music_note;
                          platformColor = AppTheme.neonRed;
                        } else if (t['platform'] == 'instagram') {
                          platformIcon = Icons.camera_alt;
                          platformColor = AppTheme.neonOrange;
                        } else if (t['platform'] == 'twitter' || t['platform'] == 'x') {
                          platformIcon = Icons.alternate_email;
                          platformColor = AppTheme.neonBlue;
                        } else if (t['platform'] == 'facebook') {
                          platformIcon = Icons.facebook;
                          platformColor = AppTheme.neonBlue;
                        }

                        final priority = _ticketPriority[tid] ?? 'medium';
                        final priorityColor = priority == 'high' ? AppTheme.neonRed : (priority == 'medium' ? AppTheme.neonYellow : AppTheme.neonGreen);

                        return Card(
                          color: isSelected ? AppTheme.secondaryColor.withOpacity(0.08) : Colors.black26,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                            side: BorderSide(color: isSelected ? AppTheme.secondaryColor : Colors.white10),
                          ),
                          margin: const EdgeInsets.only(bottom: 12),
                          child: ListTile(
                            onTap: () => setState(() => _activeTicket = t),
                            leading: Stack(
                              children: [
                                CircleAvatar(
                                  backgroundColor: AppTheme.secondaryColor.withOpacity(0.1),
                                  child: Text(t['user'][0].toUpperCase(), style: const TextStyle(fontWeight: FontWeight.bold, color: AppTheme.secondaryColor)),
                                ),
                                Positioned(
                                  right: 0,
                                  bottom: 0,
                                  child: CircleAvatar(
                                    backgroundColor: Colors.black,
                                    radius: 8,
                                    child: Icon(platformIcon, color: platformColor, size: 10),
                                  ),
                                ),
                              ],
                            ),
                            title: Row(
                              children: [
                                Text(t['user'], style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                                const Spacer(),
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                  decoration: BoxDecoration(
                                    color: priorityColor.withOpacity(0.12),
                                    borderRadius: BorderRadius.circular(4),
                                  ),
                                  child: Text(
                                    priority.toUpperCase(),
                                    style: TextStyle(color: priorityColor, fontSize: 9, fontWeight: FontWeight.bold),
                                  ),
                                ),
                              ],
                            ),
                            subtitle: Padding(
                              padding: const EdgeInsets.only(top: 4.0),
                              child: Text(
                                t['message'],
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(fontSize: 12, color: AppTheme.mutedTextColor),
                              ),
                            ),
                          ),
                        );
                      },
                    ),
            ],
          ),
        ),
        const SizedBox(width: 24),
        // Thread Details & Actions (Right Pane)
        Expanded(
          flex: 5,
          child: _activeTicket == null
              ? const Card(child: Padding(padding: EdgeInsets.all(40), child: Center(child: Text('Selecciona una conversación para ver los detalles.'))))
              : Card(
                  child: Padding(
                    padding: const EdgeInsets.all(20.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            CircleAvatar(
                              backgroundColor: AppTheme.secondaryColor,
                              foregroundColor: Colors.black,
                              child: Text(_activeTicket!['user'][0].toUpperCase(), style: const TextStyle(fontWeight: FontWeight.bold)),
                            ),
                            const SizedBox(width: 12),
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(_activeTicket!['user'], style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                                Text('Plataforma: ${_activeTicket!['platform'].toString().toUpperCase()}', style: const TextStyle(fontSize: 11, color: AppTheme.mutedTextColor)),
                              ],
                            ),
                            const Spacer(),
                            Chip(
                              label: Text('Asignado: ${_ticketAssignee[_activeTicket!['id']] ?? "AgentIA"}'),
                              avatar: const Icon(Icons.smart_toy, size: 14),
                              backgroundColor: AppTheme.secondaryColor.withOpacity(0.1),
                              labelStyle: const TextStyle(fontSize: 10, color: AppTheme.secondaryColor),
                            ),
                          ],
                        ),
                        const Divider(color: Colors.white10, height: 24),
                        const Text('Mensaje Recibido:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: AppTheme.mutedTextColor)),
                        const SizedBox(height: 6),
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: Colors.black38,
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: Colors.white10),
                          ),
                          child: Text(_activeTicket!['message'], style: const TextStyle(fontSize: 13, height: 1.4)),
                        ),
                        const SizedBox(height: 16),
                        // Dropdowns for parameters
                        Row(
                          children: [
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Text('Prioridad de Tarea', style: TextStyle(fontSize: 10, color: AppTheme.mutedTextColor)),
                                  DropdownButton<String>(
                                    isExpanded: true,
                                    value: _ticketPriority[_activeTicket!['id']] ?? 'medium',
                                    onChanged: (val) {
                                      if (val != null) {
                                        setState(() => _ticketPriority[_activeTicket!['id']] = val);
                                      }
                                    },
                                    items: const [
                                      DropdownMenuItem(value: 'low', child: Text('Baja 🟢', style: TextStyle(fontSize: 12))),
                                      DropdownMenuItem(value: 'medium', child: Text('Media 🟡', style: TextStyle(fontSize: 12))),
                                      DropdownMenuItem(value: 'high', child: Text('Alta 🔴', style: TextStyle(fontSize: 12))),
                                    ],
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Text('Sentimiento Manual', style: TextStyle(fontSize: 10, color: AppTheme.mutedTextColor)),
                                  DropdownButton<String>(
                                    isExpanded: true,
                                    value: _ticketSentiment[_activeTicket!['id']] ?? 'neutral',
                                    onChanged: (val) {
                                      if (val != null) {
                                        setState(() => _ticketSentiment[_activeTicket!['id']] = val);
                                      }
                                    },
                                    items: const [
                                      DropdownMenuItem(value: 'positive', child: Text('Positivo 🙂', style: TextStyle(fontSize: 12))),
                                      DropdownMenuItem(value: 'neutral', child: Text('Neutro 😐', style: TextStyle(fontSize: 12))),
                                      DropdownMenuItem(value: 'negative', child: Text('Negativo 🙁', style: TextStyle(fontSize: 12))),
                                    ],
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        Row(
                          children: [
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Text('Operador Asignado', style: TextStyle(fontSize: 10, color: AppTheme.mutedTextColor)),
                                  DropdownButton<String>(
                                    isExpanded: true,
                                    value: _ticketAssignee[_activeTicket!['id']] ?? 'AgentIA',
                                    onChanged: (val) {
                                      if (val != null) {
                                        setState(() => _ticketAssignee[_activeTicket!['id']] = val);
                                      }
                                    },
                                    items: const [
                                      DropdownMenuItem(value: 'AgentIA', child: Text('👤 AgentIA', style: TextStyle(fontSize: 12))),
                                      DropdownMenuItem(value: 'Nicolas Norton', child: Text('👤 N. Norton', style: TextStyle(fontSize: 12))),
                                      DropdownMenuItem(value: 'Maria Silva', child: Text('👤 M. Silva', style: TextStyle(fontSize: 12))),
                                    ],
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Text('Categoría / Tag', style: TextStyle(fontSize: 10, color: AppTheme.mutedTextColor)),
                                  DropdownButton<String>(
                                    isExpanded: true,
                                    value: _ticketCategory[_activeTicket!['id']] ?? 'Soporte',
                                    onChanged: (val) {
                                      if (val != null) {
                                        setState(() => _ticketCategory[_activeTicket!['id']] = val);
                                      }
                                    },
                                    items: const [
                                      DropdownMenuItem(value: 'Soporte', child: Text('🏷️ Soporte', style: TextStyle(fontSize: 12))),
                                      DropdownMenuItem(value: 'Feedback', child: Text('🏷️ Feedback', style: TextStyle(fontSize: 12))),
                                      DropdownMenuItem(value: 'Venta', child: Text('🏷️ Venta', style: TextStyle(fontSize: 12))),
                                      DropdownMenuItem(value: 'Facturación', child: Text('🏷️ Factura', style: TextStyle(fontSize: 12))),
                                    ],
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 20),
                        const Row(
                          children: [
                            Icon(Icons.auto_awesome, color: AppTheme.secondaryColor, size: 16),
                            SizedBox(width: 8),
                            Text('Respuesta Sugerida por Inhaus AI:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: AppTheme.secondaryColor)),
                          ],
                        ),
                        const SizedBox(height: 6),
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: AppTheme.surfaceColor,
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: AppTheme.secondaryColor.withOpacity(0.2)),
                          ),
                          child: Text(_activeTicket!['suggested_reply'], style: const TextStyle(fontSize: 13, height: 1.4)),
                        ),
                        const SizedBox(height: 20),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: [
                            ElevatedButton.icon(
                              onPressed: () {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(content: Text('Respuesta enviada a ${_activeTicket!['user']}')),
                                );
                              },
                              style: ElevatedButton.styleFrom(
                                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                              ),
                              icon: const Icon(Icons.send, size: 16),
                              label: const Text('Enviar', style: TextStyle(fontSize: 12)),
                            ),
                            OutlinedButton.icon(
                              onPressed: () => _escalateTicket('Zendesk'),
                              style: OutlinedButton.styleFrom(
                                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                              ),
                              icon: const Icon(Icons.support_agent, size: 16),
                              label: const Text('Zendesk ↗️', style: TextStyle(fontSize: 12)),
                            ),
                            OutlinedButton.icon(
                              onPressed: () => _escalateTicket('Salesforce'),
                              style: OutlinedButton.styleFrom(
                                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                              ),
                              icon: const Icon(Icons.cloud_upload_outlined, size: 16),
                              label: const Text('Salesforce ↗️', style: TextStyle(fontSize: 12)),
                            ),
                          ],
                        ),
                        
                        // Sandbox Escalation Trace Logs Box
                        if (_ticketEscalationLogs[_activeTicket!['id']] != null && _ticketEscalationLogs[_activeTicket!['id']]!.isNotEmpty) ...[
                          const SizedBox(height: 20),
                          Row(
                            children: const [
                              Icon(Icons.terminal, color: AppTheme.secondaryColor, size: 14),
                              SizedBox(width: 6),
                              Text('Sandbox Escalation Trace Logs:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 11, color: AppTheme.secondaryColor)),
                            ],
                          ),
                          const SizedBox(height: 6),
                          Container(
                            height: 160,
                            width: double.infinity,
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              color: Colors.black,
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(color: Colors.white24),
                            ),
                            child: ListView.builder(
                              itemCount: _ticketEscalationLogs[_activeTicket!['id']]!.length,
                              itemBuilder: (ctx, lIdx) {
                                final log = _ticketEscalationLogs[_activeTicket!['id']]![lIdx];
                                Color logColor = Colors.white70;
                                if (log.contains('ENDPOINT') || log.contains('PAYLOAD')) {
                                  logColor = AppTheme.neonBlue;
                                } else if (log.contains('RESPONSE') || log.contains('SUCCESS')) {
                                  logColor = AppTheme.neonGreen;
                                } else if (log.contains('STATUS')) {
                                  logColor = AppTheme.neonYellow;
                                }
                                return Text(
                                  log,
                                  style: const TextStyle(fontFamily: 'monospace', fontSize: 10, height: 1.3),
                                );
                              },
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
        ),
      ],
    );
  }

  // --- SUB TAB 1: CALENDAR & CREATOR ---
  // --- SUB TAB 1: CALENDAR & CREATOR ---
  Widget _buildVisualCalendar() {
    final days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];
    
    // Mock scheduled items with thumbnails & suggested times
    final mockCalendar = [
      {'day': 0, 'title': 'Lanzamiento de SOTA AI', 'time': '10:00 AM', 'platform': 'instagram', 'image': 'https://assets.cdn.filesafe.space/7w7j6sfnicAwqdXG0sKP/media/6a18c4e6f58810f313b89b59.png', 'viral': '10:15 AM (ViralPost®)'},
      {'day': 1, 'title': 'Estrategia de Presupuesto', 'time': '02:30 PM', 'platform': 'tiktok', 'image': 'https://assets.cdn.filesafe.space/7w7j6sfnicAwqdXG0sKP/media/6a18c4e6f58810f313b89b59.png', 'viral': '02:30 PM (ViralPost®)'},
      {'day': 3, 'title': 'Análisis de Retornos A/B', 'time': '11:15 AM', 'platform': 'twitter', 'image': 'https://assets.cdn.filesafe.space/7w7j6sfnicAwqdXG0sKP/media/6a18c4e6f58810f313b89b59.png', 'viral': '11:00 AM (ViralPost®)'},
      {'day': 4, 'title': 'Caso de Éxito Inhaus', 'time': '09:00 AM', 'platform': 'instagram', 'image': 'https://assets.cdn.filesafe.space/7w7j6sfnicAwqdXG0sKP/media/6a18c4e6f58810f313b89b59.png', 'viral': '09:30 AM (ViralPost®)'},
    ];

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: const [
                    Text('Visual Publishing Hub (Sprout Style)', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                    Text('Calendario colaborativo con optimización de horarios de publicación.', style: TextStyle(fontSize: 12, color: AppTheme.mutedTextColor)),
                  ],
                ),
                // Toggle view modes
                Container(
                  padding: const EdgeInsets.all(2),
                  decoration: BoxDecoration(
                    color: Colors.white10,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    children: [
                      ElevatedButton(
                        onPressed: () => setState(() => _publishingViewMode = 0),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: _publishingViewMode == 0 ? AppTheme.secondaryColor : Colors.transparent,
                          foregroundColor: _publishingViewMode == 0 ? Colors.black : Colors.white70,
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                          elevation: 0,
                        ),
                        child: const Text('Calendario', style: TextStyle(fontSize: 11)),
                      ),
                      ElevatedButton(
                        onPressed: () => setState(() => _publishingViewMode = 1),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: _publishingViewMode == 1 ? AppTheme.secondaryColor : Colors.transparent,
                          foregroundColor: _publishingViewMode == 1 ? Colors.black : Colors.white70,
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                          elevation: 0,
                        ),
                        child: const Text('Aprobaciones (Kanban)', style: TextStyle(fontSize: 11)),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),
            
            // View Mode Rendering
            if (_publishingViewMode == 0)
              GridView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 7,
                  crossAxisSpacing: 8,
                  mainAxisSpacing: 8,
                  childAspectRatio: 0.52,
                ),
                itemCount: 7,
                itemBuilder: (context, index) {
                  final dayName = days[index];
                  final items = mockCalendar.where((item) => item['day'] == index).toList();

                  return Container(
                    decoration: BoxDecoration(
                      color: Colors.black26,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: Colors.white10),
                    ),
                    padding: const EdgeInsets.all(8),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(dayName, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 11, color: AppTheme.tertiaryColor)),
                        const Divider(color: Colors.white10, height: 12),
                        Expanded(
                          child: ListView.builder(
                            itemCount: items.length,
                            itemBuilder: (ctx, itemIdx) {
                              final item = items[itemIdx];
                              return Card(
                                color: AppTheme.surfaceColor,
                                margin: const EdgeInsets.only(bottom: 6),
                                child: Padding(
                                  padding: const EdgeInsets.all(4.0),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      ClipRRect(
                                        borderRadius: BorderRadius.circular(4),
                                        child: Image.network(
                                          item['image'] as String,
                                          height: 50,
                                          width: double.infinity,
                                          fit: BoxFit.cover,
                                          errorBuilder: (context, error, stackTrace) => Container(color: Colors.white10, height: 50),
                                        ),
                                      ),
                                      const SizedBox(height: 4),
                                      Text(item['title'] as String, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 9, fontWeight: FontWeight.bold)),
                                      const SizedBox(height: 2),
                                      Row(
                                        children: [
                                          Icon(
                                            item['platform'] == 'instagram' ? Icons.camera_alt : (item['platform'] == 'tiktok' ? Icons.music_note : Icons.alternate_email),
                                            size: 10,
                                            color: AppTheme.secondaryColor,
                                          ),
                                          const SizedBox(width: 4),
                                          Text(item['time'] as String, style: const TextStyle(fontSize: 8, color: AppTheme.mutedTextColor)),
                                        ],
                                      ),
                                      const SizedBox(height: 4),
                                      // ViralPost suggested time label
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
                                        decoration: BoxDecoration(
                                          color: AppTheme.secondaryColor.withOpacity(0.12),
                                          borderRadius: BorderRadius.circular(4),
                                        ),
                                        child: Row(
                                          children: [
                                            const Icon(Icons.bolt, color: AppTheme.secondaryColor, size: 8),
                                            const SizedBox(width: 2),
                                            Expanded(
                                              child: Text(
                                                item['viral'] as String,
                                                style: const TextStyle(fontSize: 7, color: AppTheme.secondaryColor, fontWeight: FontWeight.bold),
                                                maxLines: 1,
                                                overflow: TextOverflow.ellipsis,
                                              ),
                                            ),
                                          ],
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              );
                            },
                          ),
                        ),
                      ],
                    ),
                  );
                },
              )
            else
              // Kanban Approval Flow Board
              SizedBox(
                height: 380,
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Expanded(child: _buildKanbanColumn('Borrador', 'Borrador')),
                    Expanded(child: _buildKanbanColumn('Pendiente de Cliente', 'Pendiente de Cliente')),
                    Expanded(child: _buildKanbanColumn('Aprobado', 'Aprobado')),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildKanbanColumn(String title, String status) {
    final columnPosts = _approvalPosts.where((p) => p['status'] == status).toList();
    return DragTarget<String>(
      onAccept: (postId) {
        setState(() {
          final post = _approvalPosts.firstWhere((p) => p['id'] == postId);
          post['status'] = status;
        });
      },
      onAcceptWithDetails: (details) {
        setState(() {
          final post = _approvalPosts.firstWhere((p) => p['id'] == details.data);
          post['status'] = status;
        });
      },
      builder: (context, candidateData, rejectedData) {
        return Container(
          margin: const EdgeInsets.symmetric(horizontal: 4),
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: candidateData.isNotEmpty ? AppTheme.secondaryColor.withOpacity(0.05) : Colors.black26,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: candidateData.isNotEmpty ? AppTheme.secondaryColor : Colors.white10),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Text(
                      title,
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: AppTheme.primaryColor),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: Colors.white12,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Text('${columnPosts.length}', style: const TextStyle(fontSize: 10)),
                  ),
                ],
              ),
              const Divider(color: Colors.white10, height: 16),
              Expanded(
                child: ListView.builder(
                  itemCount: columnPosts.length,
                  itemBuilder: (ctx, idx) {
                    final post = columnPosts[idx];
                    return Draggable<String>(
                      data: post['id'] as String,
                      feedback: Material(
                        color: Colors.transparent,
                        child: Container(
                          width: 200,
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            color: Colors.grey.shade900,
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: AppTheme.secondaryColor),
                          ),
                          child: Text(post['title'] as String, style: const TextStyle(color: Colors.white, fontSize: 11)),
                        ),
                      ),
                      childWhenDragging: Opacity(
                        opacity: 0.4,
                        child: _buildPostCard(post),
                      ),
                      child: _buildPostCard(post),
                    );
                  },
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildPostCard(Map<String, dynamic> post) {
    IconData platformIcon = Icons.link;
    if (post['platform'] == 'instagram') {
      platformIcon = Icons.camera_alt;
    } else if (post['platform'] == 'tiktok') {
      platformIcon = Icons.music_note;
    } else if (post['platform'] == 'twitter' || post['platform'] == 'x') {
      platformIcon = Icons.alternate_email;
    } else if (post['platform'] == 'linkedin') {
      platformIcon = Icons.business;
    }

    return Card(
      color: AppTheme.surfaceColor,
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.all(8.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(platformIcon, size: 12, color: AppTheme.secondaryColor),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    post['title'] as String,
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 11),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(post['content'] as String, style: const TextStyle(fontSize: 10, color: AppTheme.mutedTextColor), maxLines: 2, overflow: TextOverflow.ellipsis),
            const SizedBox(height: 6),
            Row(
              children: [
                const Icon(Icons.bolt, color: AppTheme.secondaryColor, size: 8),
                const SizedBox(width: 2),
                Expanded(
                  child: Text(
                    post['viral_time'] as String,
                    style: const TextStyle(fontSize: 7, color: AppTheme.secondaryColor, fontWeight: FontWeight.bold),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                if (post['status'] != 'Borrador')
                  IconButton(
                    icon: const Icon(Icons.arrow_back, size: 12, color: AppTheme.mutedTextColor),
                    onPressed: () {
                      setState(() {
                        if (post['status'] == 'Aprobado') {
                          post['status'] = 'Pendiente de Cliente';
                        } else if (post['status'] == 'Pendiente de Cliente') {
                          post['status'] = 'Borrador';
                        }
                      });
                    },
                    tooltip: 'Mover al estado anterior',
                    constraints: const BoxConstraints(),
                    padding: EdgeInsets.zero,
                  ),
                if (post['status'] != 'Aprobado')
                  IconButton(
                    icon: const Icon(Icons.arrow_forward, size: 12, color: AppTheme.secondaryColor),
                    onPressed: () {
                      setState(() {
                        if (post['status'] == 'Borrador') {
                          post['status'] = 'Pendiente de Cliente';
                        } else if (post['status'] == 'Pendiente de Cliente') {
                          post['status'] = 'Aprobado';
                        }
                      });
                    },
                    tooltip: post['status'] == 'Borrador' ? 'Enviar a Cliente' : 'Aprobar Post',
                    constraints: const BoxConstraints(),
                    padding: EdgeInsets.zero,
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildIPhoneFrame({required Widget child}) {
    return Container(
      width: 290,
      height: 520,
      padding: const EdgeInsets.fromLTRB(12, 28, 12, 12),
      decoration: BoxDecoration(
        color: Colors.black,
        borderRadius: BorderRadius.circular(36),
        border: Border.all(color: AppTheme.tertiaryColor, width: 4),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.5),
            blurRadius: 15,
            spreadRadius: 2,
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(24),
        child: Container(
          color: AppTheme.backgroundColor,
          child: child,
        ),
      ),
    );
  }

  Widget _buildMockMobilePreview() {
    String hook = _analysisResults?['hook'] ?? 'Capturando atención...';
    String narrative = _analysisResults?['narrative_arc'] ?? 'Detalle del post social...';
    String promptText = _analysisResults?['script_prompt'] ?? 'Boceto creativo';

    return _buildIPhoneFrame(
      child: Scaffold(
        backgroundColor: Colors.black,
        body: Column(
          children: [
            // Status bar
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: const [
                  Text('12:00', style: TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold)),
                  Icon(Icons.battery_std, color: Colors.white, size: 10),
                ],
              ),
            ),
            // Brand Logo Header
            ListTile(
              dense: true,
              leading: CircleAvatar(
                radius: 12,
                backgroundColor: AppTheme.secondaryColor,
                child: const Text('I', style: TextStyle(fontSize: 8, color: Colors.black)),
              ),
              title: const Text('inhaus_creative', style: TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.bold)),
              subtitle: const Text('Patrocinado', style: TextStyle(color: Colors.white54, fontSize: 8)),
              trailing: const Icon(Icons.more_horiz, color: Colors.white),
            ),
            // Mock Video Content W/ Slider points
            Expanded(
              flex: 5,
              child: Container(
                color: Colors.grey[900],
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    Image.network(
                      'https://assets.cdn.filesafe.space/7w7j6sfnicAwqdXG0sKP/media/6a18c4e6f58810f313b89b59.png',
                      fit: BoxFit.cover,
                      height: double.infinity,
                      width: double.infinity,
                    ),
                    Container(color: Colors.black38),
                    const Icon(Icons.play_circle_fill, color: Colors.white70, size: 48),
                    // Video HUD overlays
                    Positioned(
                      bottom: 12,
                      left: 12,
                      right: 12,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: AppTheme.secondaryColor,
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(
                              _timelineValue <= 3.0 ? 'HOOK' : (_timelineValue <= 12.0 ? 'DESARROLLO' : 'CTA'),
                              style: const TextStyle(color: Colors.black, fontSize: 8, fontWeight: FontWeight.bold),
                            ),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            _timelineValue <= 3.0 ? hook : (_timelineValue <= 12.0 ? narrative : 'Llamado a la Acción final'),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
            // Footer Info
            Expanded(
              flex: 2,
              child: Container(
                padding: const EdgeInsets.all(12),
                color: Colors.black,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: const [
                        Icon(Icons.favorite_border, color: Colors.white, size: 18),
                        SizedBox(width: 12),
                        Icon(Icons.mode_comment_outlined, color: Colors.white, size: 18),
                        SizedBox(width: 12),
                        Icon(Icons.send_outlined, color: Colors.white, size: 18),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      promptText,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: Colors.white70, fontSize: 9),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDeconstructionAndGenerator() {
    return Column(
      children: [
        // reverse engineer with smartphone mock preview
        Card(
          child: Padding(
            padding: const EdgeInsets.all(20.0),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  flex: 3,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Deconstrucción y Simulador de Posts', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                      const Text('Convierte vídeos virales públicos en mockups y prompts de marca.', style: TextStyle(fontSize: 12, color: AppTheme.mutedTextColor)),
                      const SizedBox(height: 16),
                      TextField(
                        controller: _urlController,
                        decoration: const InputDecoration(
                          hintText: 'Enlace del vídeo (TikTok, Reels, Shorts)',
                          prefixIcon: Icon(Icons.link),
                        ),
                      ),
                      const SizedBox(height: 12),
                      ElevatedButton.icon(
                        onPressed: _analyzing ? null : _analyzeVideo,
                        icon: _analyzing
                            ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black))
                            : const Icon(Icons.auto_mode),
                        label: const Text('Deconstruir en Móvil'),
                      ),
                      if (_analysisResults != null) ...[
                        const SizedBox(height: 20),
                        const Divider(color: Colors.white10),
                        const SizedBox(height: 8),
                        const Text('Línea de Tiempo del Script (Interactivo):', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: AppTheme.secondaryColor)),
                        Slider(
                          value: _timelineValue,
                          max: 15.0,
                          divisions: 15,
                          label: '${_timelineValue.toStringAsFixed(1)}s',
                          activeColor: AppTheme.secondaryColor,
                          inactiveColor: Colors.white10,
                          onChanged: (val) {
                            setState(() => _timelineValue = val);
                          },
                        ),
                        _buildTimelineIndicatorCard(),
                      ],
                    ],
                  ),
                ),
                const SizedBox(width: 24),
                // Smartphone mockup display
                Column(
                  children: [
                    const Text('Post Mockup', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: AppTheme.secondaryColor)),
                    const SizedBox(height: 8),
                    _buildMockMobilePreview(),
                  ],
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 24),
        // comparative generator with aspect ratios
        Card(
          child: Padding(
            padding: const EdgeInsets.all(20.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Generación de Video A/B (Veo 3 vs Sora 2)', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                const Text('Previsualiza y compara resultados creativos según la orientación del formato.', style: TextStyle(fontSize: 12, color: AppTheme.mutedTextColor)),
                const SizedBox(height: 16),
                
                // Aspect Ratio Selector
                Row(
                  children: [
                    const Text('Relación de Aspecto (Formato):', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                    const SizedBox(width: 12),
                    ...['9:16 Vertical', '16:9 Horizontal', '1:1 Cuadrado'].map((ratio) {
                      final active = _selectedAspectRatio == ratio.split(' ')[0];
                      return Padding(
                        padding: const EdgeInsets.only(right: 8.0),
                        child: ChoiceChip(
                          label: Text(ratio),
                          selected: active,
                          onSelected: (val) {
                            if (val) setState(() => _selectedAspectRatio = ratio.split(' ')[0]);
                          },
                        ),
                      );
                    }),
                  ],
                ),
                const SizedBox(height: 16),

                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _promptController,
                        maxLines: 2,
                        decoration: const InputDecoration(
                          hintText: 'Ingresa el prompt detallado para el generador...',
                        ),
                      ),
                    ),
                    const SizedBox(width: 16),
                    ElevatedButton(
                      onPressed: _generating ? null : _generateMedia,
                      child: _generating
                          ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black))
                          : const Text('Generar A/B'),
                    ),
                  ],
                ),
                if (_generationResults != null || _generating) ...[
                  const SizedBox(height: 20),
                  Row(
                    children: [
                      Expanded(
                        child: _buildMediaPreviewFrame(_selectedModelA.toUpperCase(), 'https://storage.googleapis.com/sota-media/veo3_demo.mp4'),
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: _buildMediaPreviewFrame(_selectedModelB.toUpperCase(), 'https://storage.googleapis.com/sota-media/sora2_demo.mp4'),
                      ),
                    ],
                  ),
                ],
              ],
            ),
          ),
        ),
      ],
    );
  }

  // --- SUB TAB 2: LISTENING & ANALYTICS ---
  Widget _buildListeningAnalytics() {
    return Column(
      children: [
        // Message Spike Alert Banner
        Container(
          margin: const EdgeInsets.only(bottom: 24),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AppTheme.neonOrange.withOpacity(0.12),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AppTheme.neonOrange, width: 1.5),
          ),
          child: Row(
            children: [
              const Icon(Icons.warning_amber_rounded, color: AppTheme.neonOrange, size: 28),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: const [
                    Text(
                      '⚠️ SPIKE WARNING ALERT: Menciones Anómalas Detectadas',
                      style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: AppTheme.neonOrange),
                    ),
                    SizedBox(height: 2),
                    Text(
                      'El volumen de menciones para Inhaus ha superado la media diaria en un 247% en las últimas 2 horas. Posible conversación viral o crisis de reputación detectada en Reddit y X.',
                      style: TextStyle(fontSize: 11, color: AppTheme.primaryColor),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              ElevatedButton(
                onPressed: () {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Analizando orígenes del pico de menciones en tiempo real...')),
                  );
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.neonOrange,
                  foregroundColor: Colors.black,
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                ),
                child: const Text('Ver Spike', style: TextStyle(fontSize: 11)),
              ),
            ],
          ),
        ),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Sentiment Trend
            Expanded(
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(20.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Sentiment & Health Analytics', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                      const Text('Evolución del sentimiento de marca en menciones sociales.', style: TextStyle(fontSize: 12, color: AppTheme.mutedTextColor)),
                      const SizedBox(height: 16),
                      Container(
                        height: 220,
                        width: double.infinity,
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.black26,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: Colors.white10),
                        ),
                        child: CustomPaint(
                          painter: SentimentChartPainter(),
                        ),
                      ),
                      const SizedBox(height: 12),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                        children: [
                          _buildChartLegend(AppTheme.neonGreen, 'Positivo'),
                          _buildChartLegend(AppTheme.neonYellow, 'Neutral'),
                          _buildChartLegend(AppTheme.neonRed, 'Negativo'),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(width: 24),
            // Word Cloud & SOV
            Expanded(
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(20.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Share of Voice (SOV) & Nube de Palabras', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                      const Text('Métricas de presencia e impacto de marca frente a competidores.', style: TextStyle(fontSize: 12, color: AppTheme.mutedTextColor)),
                      const SizedBox(height: 16),
                      // Share of voice representation
                      Container(
                        height: 120,
                        decoration: BoxDecoration(
                          color: Colors.black26,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: Colors.white10),
                        ),
                        padding: const EdgeInsets.all(12),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: const [
                                Text('Share of Voice Competitivo', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                                Text('Inhaus (58%) vs Otros', style: TextStyle(fontSize: 11, color: AppTheme.secondaryColor, fontWeight: FontWeight.bold)),
                              ],
                            ),
                            const SizedBox(height: 12),
                            // Stacked SOV Bar Chart
                            ClipRRect(
                              borderRadius: BorderRadius.circular(6),
                              child: SizedBox(
                                height: 16,
                                child: Row(
                                  children: [
                                    Expanded(flex: 58, child: Container(color: AppTheme.secondaryColor)),
                                    Expanded(flex: 22, child: Container(color: AppTheme.tertiaryColor)),
                                    Expanded(flex: 12, child: Container(color: AppTheme.neonBlue)),
                                    Expanded(flex: 8, child: Container(color: AppTheme.neonRed)),
                                  ],
                                ),
                              ),
                            ),
                            const SizedBox(height: 10),
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                _buildChartLegend(AppTheme.secondaryColor, 'Inhaus (58%)'),
                                _buildChartLegend(AppTheme.tertiaryColor, 'Brand X (22%)'),
                                _buildChartLegend(AppTheme.neonBlue, 'Brand Y (12%)'),
                                _buildChartLegend(AppTheme.neonRed, 'Brand Z (8%)'),
                              ],
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 20),
                      // Word Cloud chips
                      const Text('Palabras Clave en Tendencia:', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: const [
                          Chip(label: Text('Inhaus'), backgroundColor: Colors.white10),
                          Chip(label: Text('SOTA Ads', style: TextStyle(color: AppTheme.secondaryColor)), backgroundColor: Colors.white24),
                          Chip(label: Text('Automation'), backgroundColor: Colors.white10),
                          Chip(label: Text('Meta ROI'), backgroundColor: Colors.white10),
                          Chip(label: Text('Veo3 Video'), backgroundColor: Colors.white24),
                          Chip(label: Text('SLA 15m'), backgroundColor: Colors.white10),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    Widget activeContent = const SizedBox.shrink();
    if (_subTabIndex == 0) {
      activeContent = _buildSmartInbox();
    } else if (_subTabIndex == 1) {
      activeContent = Column(
        children: [
          _buildVisualCalendar(),
          const SizedBox(height: 24),
          _buildDeconstructionAndGenerator(),
        ],
      );
    } else if (_subTabIndex == 2) {
      activeContent = _buildListeningAnalytics();
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.trending_up, color: AppTheme.secondaryColor, size: 28),
              const SizedBox(width: 12),
              Text(
                'Social Media Studio (Sprout Style)',
                style: Theme.of(context).textTheme.headlineMedium,
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Ideación de viralidad, inbox centralizado y planificador de publicación de contenidos para agencias creativas.',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppTheme.mutedTextColor),
          ),
          const SizedBox(height: 24),
          _buildSubTabBar(),
          activeContent,
        ],
      ),
    );
  }

  Widget _buildTimelineIndicatorCard() {
    String stepTitle = '0-3s Hook Inicial';
    String stepDesc = 'Una pregunta o reto visual para captar la atención del usuario.';
    Color stepColor = AppTheme.neonRed;

    if (_timelineValue > 3.0 && _timelineValue <= 12.0) {
      stepTitle = '3-12s Arco Narrativo';
      stepDesc = 'Desarrollo de la frustración del usuario y presentación de la solución.';
      stepColor = AppTheme.neonBlue;
    } else if (_timelineValue > 12.0) {
      stepTitle = '12-15s Llamado a la Acción (CTA)';
      stepDesc = 'Cierre con llamado claro a visitar la web o registrarse.';
      stepColor = AppTheme.neonGreen;
    }

    return Card(
      color: Colors.black26,
      margin: const EdgeInsets.only(top: 8, bottom: 16),
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Row(
          children: [
            Container(
              width: 8,
              height: 40,
              decoration: BoxDecoration(
                color: stepColor,
                borderRadius: BorderRadius.circular(4),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(stepTitle, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                  Text(stepDesc, style: const TextStyle(fontSize: 11, color: AppTheme.mutedTextColor)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMediaPreviewFrame(String title, String url) {
    // Modify layout sizes depending on aspect ratio selection
    double frameHeight = 180;
    double frameWidth = double.infinity;
    if (_selectedAspectRatio == '9:16') {
      frameHeight = 240;
    } else if (_selectedAspectRatio == '1:1') {
      frameHeight = 180;
    }
    
    return Container(
      height: frameHeight,
      width: frameWidth,
      decoration: BoxDecoration(
        color: Colors.black45,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white10),
      ),
      child: Stack(
        children: [
          Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.play_circle_outline, size: 48, color: AppTheme.primaryColor),
                const SizedBox(height: 8),
                Text('Render ($title - $_selectedAspectRatio)', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
              ],
            ),
          ),
          Positioned(
            top: 8,
            right: 8,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: Colors.black54,
                borderRadius: BorderRadius.circular(4),
              ),
              child: Text(title, style: const TextStyle(fontSize: 10, color: AppTheme.secondaryColor)),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildChartLegend(Color color, String text) {
    return Row(
      children: [
        Container(width: 8, height: 8, decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
        const SizedBox(width: 6),
        Text(text, style: const TextStyle(fontSize: 10, color: AppTheme.mutedTextColor)),
      ],
    );
  }
}

class SentimentChartPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final gridPaint = Paint()
      ..color = Colors.white10
      ..strokeWidth = 1.0;

    for (double i = 0; i <= size.width; i += size.width / 4) {
      canvas.drawLine(Offset(i, 0), Offset(i, size.height), gridPaint);
    }
    for (double i = 0; i <= size.height; i += size.height / 3) {
      canvas.drawLine(Offset(0, i), Offset(size.width, i), gridPaint);
    }

    final positivePaint = Paint()
      ..color = AppTheme.neonGreen
      ..strokeWidth = 3.0
      ..style = PaintingStyle.stroke;

    final negativePaint = Paint()
      ..color = AppTheme.neonRed
      ..strokeWidth = 3.0
      ..style = PaintingStyle.stroke;

    final positivePath = Path()
      ..moveTo(0, size.height * 0.4)
      ..cubicTo(size.width * 0.25, size.height * 0.3, size.width * 0.5, size.height * 0.6, size.width * 0.75, size.height * 0.2)
      ..lineTo(size.width, size.height * 0.15);

    final negativePath = Path()
      ..moveTo(0, size.height * 0.8)
      ..cubicTo(size.width * 0.25, size.height * 0.7, size.width * 0.5, size.height * 0.5, size.width * 0.75, size.height * 0.8)
      ..lineTo(size.width, size.height * 0.9);

    canvas.drawPath(positivePath, positivePaint);
    canvas.drawPath(negativePath, negativePaint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
