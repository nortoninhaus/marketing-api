import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/providers.dart';
import '../../theme/app_theme.dart';

class ModoIaTab extends ConsumerStatefulWidget {
  const ModoIaTab({super.key});

  @override
  ConsumerState<ModoIaTab> createState() => _ModoIaTabState();
}

class _ModoIaTabState extends ConsumerState<ModoIaTab> {
  List<dynamic> _brandProfiles = [];
  List<dynamic> _agentSkills = [];
  bool _loadingProfiles = false;
  bool _loadingSkills = false;

  final TextEditingController _promptController = TextEditingController(text: 'Escribe un borrador para responder al tweet sobre TikTok Ads indicando que Inhaus simplifica los reportes en un 50%.');
  String _iaOutput = '';
  bool _generating = false;

  // Skill debugger states
  final Map<String, String> _skillInputs = {};
  final Map<String, List<String>> _skillDebugLogs = {};
  final Map<String, bool> _skillExpanded = {};

  @override
  void initState() {
    super.initState();
    _loadProfiles();
    _loadSkills();
  }

  Future<void> _loadProfiles() async {
    setState(() => _loadingProfiles = true);
    try {
      final client = ref.read(apiClientProvider);
      final res = await client.getBrandProfiles();
      setState(() {
        _brandProfiles = res;
      });
    } catch (e) {
      debugPrint('Failed to load brand profiles: $e');
    } finally {
      setState(() => _loadingProfiles = false);
    }
  }

  Future<void> _loadSkills() async {
    setState(() => _loadingSkills = true);
    try {
      final client = ref.read(apiClientProvider);
      final res = await client.getAgentSkills();
      setState(() {
        _agentSkills = res;
      });
    } catch (e) {
      debugPrint('Failed to load agent skills: $e');
    } finally {
      setState(() => _loadingSkills = false);
    }
  }

  void _runIaPrompt() {
    setState(() {
      _generating = true;
      _iaOutput = '';
    });
    Future.delayed(const Duration(seconds: 1), () {
      setState(() {
        _generating = false;
        _iaOutput = 'Respuesta Sugerida (Reddit / Twitter):\n"Hola @dev_brand, entiendo tu frustración. Nosotros usamos Inhaus y logramos reducir la fatiga en reportes de Meta y TikTok a la mitad configurando un solo dashboard dinámico de marca blanca. ¡Pruébalo!"';
      });
    });
  }

  void _testSkill(String skillName) {
    final inputVal = _skillInputs[skillName] ?? 'ejecutar';
    setState(() {
      _skillDebugLogs[skillName] = [
        '[System] Inicializando invocación de habilidad "$skillName"...',
        '[Stitch MCP] Input: {"query": "$inputVal"}',
        '[Stitch MCP] Resolviendo esquema de parámetros...',
        '[Stitch MCP] Ejecutando llamada de herramienta en sandbox...',
      ];
    });

    Future.delayed(const Duration(milliseconds: 400), () {
      if (!mounted) return;
      setState(() {
        _skillDebugLogs[skillName]!.addAll([
          '[Stitch MCP] API Status: 200 OK',
          '[Stitch MCP] Payload de Salida: {"success": true, "result": "Mock data generated successfully for query: $inputVal"}',
          '[System] Ejecución de herramienta completada.'
        ]);
      });
    });
  }

  Widget _buildBrandProfilesCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Perfiles de Identidad de Marca (AI Brand Profiles)', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const Text('Registra misión, tono y reglas corporativas de tus clientes para reescritura automática de campañas.', style: TextStyle(fontSize: 12, color: AppTheme.mutedTextColor)),
            const SizedBox(height: 16),
            _loadingProfiles
                ? const Center(child: CircularProgressIndicator())
                : _brandProfiles.isEmpty
                    ? const Text('No hay perfiles configurados.')
                    : ListView.builder(
                        shrinkWrap: true,
                        physics: const NeverScrollableScrollPhysics(),
                        itemCount: _brandProfiles.length,
                        itemBuilder: (context, idx) {
                          final p = _brandProfiles[idx];
                          return Card(
                            color: Colors.black26,
                            margin: const EdgeInsets.only(bottom: 8),
                            child: ListTile(
                              leading: const Icon(Icons.palette_outlined, color: AppTheme.secondaryColor),
                              title: Text(p['name']),
                              subtitle: Text('Tono: ${p['tone']}\nMisión: ${p['mission']}'),
                              trailing: IconButton(
                                icon: const Icon(Icons.copy, color: AppTheme.tertiaryColor),
                                onPressed: () {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(content: Text('Perfil de marca "${p['name']}" copiado al portapapeles de la IA.')),
                                  );
                                },
                              ),
                            ),
                          );
                        },
                      ),
          ],
        ),
      ),
    );
  }

  Widget _buildIaPromptCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Ejecución Conversacional Unificada', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const Text('Ingresa instrucciones directas y observa la ejecución de tus agentes de IA.', style: TextStyle(fontSize: 12, color: AppTheme.mutedTextColor)),
            const SizedBox(height: 16),
            TextField(
              controller: _promptController,
              maxLines: 2,
              decoration: const InputDecoration(
                hintText: 'Ej. Genera un borrador para la alerta de Reddit de Inhaus...',
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                ElevatedButton.icon(
                  onPressed: _generating ? null : _runIaPrompt,
                  icon: const Icon(Icons.smart_toy),
                  label: const Text('Ejecutar Agente'),
                ),
              ],
            ),
            if (_generating) ...[
              const SizedBox(height: 16),
              const LinearProgressIndicator(color: AppTheme.secondaryColor),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildArtifactsCanvas() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.black45,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.secondaryColor.withOpacity(0.5), width: 1.5),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.art_track, color: AppTheme.secondaryColor, size: 20),
              const SizedBox(width: 8),
              const Text(
                'Lienzo de Contenido Generado (AI Artifacts Canvas)',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
              ),
            ],
          ),
          const Divider(color: Colors.white10, height: 24),
          if (_iaOutput.isEmpty && !_generating)
            const Center(
              child: Padding(
                padding: EdgeInsets.symmetric(vertical: 40.0),
                child: Column(
                  children: [
                    Icon(Icons.hourglass_empty, color: AppTheme.mutedTextColor, size: 36),
                    SizedBox(height: 12),
                    Text(
                      'Esperando la ejecución del agente conversacional...',
                      style: TextStyle(color: AppTheme.mutedTextColor, fontSize: 12),
                    ),
                  ],
                ),
              ),
            )
          else if (_generating)
            const Center(
              child: Padding(
                padding: EdgeInsets.symmetric(vertical: 40.0),
                child: Text('Generando respuesta sugerida por IA...', style: TextStyle(color: AppTheme.mutedTextColor)),
              ),
            )
          else
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.black54,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.white10),
              ),
              child: SelectableText(
                _iaOutput,
                style: const TextStyle(fontSize: 13, height: 1.5),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildSkillsCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Registro de Habilidades (Stitch/Odoo MCP)', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const Text('Equipa a tus agentes con integraciones para acceder a bases de datos o consolas externas.', style: TextStyle(fontSize: 12, color: AppTheme.mutedTextColor)),
            const SizedBox(height: 16),
            _loadingSkills
                ? const Center(child: CircularProgressIndicator())
                : _agentSkills.isEmpty
                    ? const Text('No hay habilidades cargadas.')
                    : ListView.builder(
                        shrinkWrap: true,
                        physics: const NeverScrollableScrollPhysics(),
                        itemCount: _agentSkills.length,
                        itemBuilder: (context, idx) {
                          final s = _agentSkills[idx];
                          final skillName = s['name'].toString();
                          final isExpanded = _skillExpanded[skillName] ?? false;
                          final logs = _skillDebugLogs[skillName] ?? [];

                          return Card(
                            color: Colors.black26,
                            margin: const EdgeInsets.only(bottom: 12),
                            child: Column(
                              children: [
                                SwitchListTile(
                                  secondary: const Icon(Icons.bolt, color: AppTheme.secondaryColor),
                                  title: Text(skillName, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                                  subtitle: Text(s['description'], style: const TextStyle(fontSize: 11)),
                                  value: s['enabled'],
                                  onChanged: (val) {
                                    setState(() {
                                      s['enabled'] = val;
                                    });
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      SnackBar(content: Text('Habilidad "$skillName" ${val ? 'habilitada' : 'deshabilitada'}.')),
                                    );
                                  },
                                ),
                                if (s['enabled']) ...[
                                  const Divider(color: Colors.white10, height: 1),
                                  ExpansionTile(
                                    title: const Text('Depurar Habilidad (Debugger Console)', style: TextStyle(fontSize: 11, color: AppTheme.secondaryColor, fontWeight: FontWeight.bold)),
                                    onExpansionChanged: (expanded) {
                                      setState(() {
                                        _skillExpanded[skillName] = expanded;
                                      });
                                    },
                                    children: [
                                      Padding(
                                        padding: const EdgeInsets.all(12.0),
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.stretch,
                                          children: [
                                            TextField(
                                              decoration: const InputDecoration(
                                                labelText: 'Parámetro de Entrada (Query)',
                                                isDense: true,
                                              ),
                                              style: const TextStyle(fontSize: 12),
                                              onChanged: (val) {
                                                _skillInputs[skillName] = val;
                                              },
                                            ),
                                            const SizedBox(height: 10),
                                            ElevatedButton(
                                              onPressed: () => _testSkill(skillName),
                                              style: ElevatedButton.styleFrom(
                                                padding: const EdgeInsets.symmetric(vertical: 8),
                                              ),
                                              child: const Text('Test Habilidad', style: TextStyle(fontSize: 12)),
                                            ),
                                            if (logs.isNotEmpty) ...[
                                              const SizedBox(height: 12),
                                              Container(
                                                height: 120,
                                                padding: const EdgeInsets.all(8),
                                                color: Colors.black,
                                                child: ListView.builder(
                                                  itemCount: logs.length,
                                                  itemBuilder: (ctx, logIdx) {
                                                    return Text(
                                                      logs[logIdx],
                                                      style: const TextStyle(
                                                        color: AppTheme.neonGreen,
                                                        fontFamily: 'monospace',
                                                        fontSize: 10,
                                                      ),
                                                    );
                                                  },
                                                ),
                                              ),
                                            ],
                                          ],
                                        ),
                                      ),
                                    ],
                                  ),
                                ],
                              ],
                            ),
                          );
                        },
                      ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final isWide = constraints.maxWidth > 960;
        
        final leftPane = Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildBrandProfilesCard(),
            const SizedBox(height: 24),
            _buildIaPromptCard(),
          ],
        );

        final rightPane = Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildArtifactsCanvas(),
            const SizedBox(height: 24),
            _buildSkillsCard(),
          ],
        );

        return SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.rocket_launch, color: AppTheme.secondaryColor, size: 28),
                  const SizedBox(width: 12),
                  Text(
                    'Modo IA: Espacio de Orquestación Multiagente',
                    style: Theme.of(context).textTheme.headlineMedium,
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                'Workspace de lenguaje natural para coordinar tareas cruzadas, perfiles de marca y habilidades de agente especializadas (Stitch/Odoo MCP).',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppTheme.mutedTextColor),
              ),
              const SizedBox(height: 24),
              if (isWide)
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(child: leftPane),
                    const SizedBox(width: 24),
                    Expanded(child: rightPane),
                  ],
                )
              else
                Column(
                  children: [
                    leftPane,
                    const SizedBox(height: 24),
                    rightPane,
                  ],
                ),
            ],
          ),
        );
      },
    );
  }
}
