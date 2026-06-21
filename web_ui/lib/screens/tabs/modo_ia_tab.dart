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

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.rocket_launch, color: AppTheme.primaryColor, size: 28),
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

          // Section 1: AI Brand Profiles
          Card(
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
                                  color: Colors.black25,
                                  margin: const EdgeInsets.only(bottom: 8),
                                  child: ListTile(
                                    leading: const Icon(Icons.palette_outlined, color: AppTheme.primaryColor),
                                    title: Text(p['name']),
                                    subtitle: Text('Tono: ${p['tone']}\nMisión: ${p['mission']}'),
                                    trailing: IconButton(
                                      icon: const Icon(Icons.copy, color: AppTheme.secondaryColor),
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
          ),

          const SizedBox(height: 24),

          // Section 2: Conversational Agent Execution
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Ejecución Conversacional Unificada', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  const Text('Ingresa instrucciones directas y observa la ejecución y registros de tus agentes de IA.', style: TextStyle(fontSize: 12, color: AppTheme.mutedTextColor)),
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
                    const LinearProgressIndicator(color: AppTheme.primaryColor),
                  ],
                  if (_iaOutput.isNotEmpty) ...[
                    const SizedBox(height: 20),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.black45,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Colors.white10),
                      ),
                      child: Text(_iaOutput),
                    ),
                  ],
                ],
              ),
            ),
          ),

          const SizedBox(height: 24),

          // Section 3: Agent Skills Registry
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Registro de Habilidades de Agente (Agent Skills)', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  const Text('Equipa a tus agentes con integraciones del estándar Stitch MCP u Odoo para acceder a inventarios o planillas.', style: TextStyle(fontSize: 12, color: AppTheme.mutedTextColor)),
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
                                return Card(
                                  color: Colors.black25,
                                  margin: const EdgeInsets.only(bottom: 8),
                                  child: SwitchListTile(
                                    secondary: const Icon(Icons.bolt, color: AppTheme.primaryColor),
                                    title: Text(s['name']),
                                    subtitle: Text(s['description']),
                                    value: s['enabled'],
                                    onChanged: (val) {
                                      setState(() {
                                        s['enabled'] = val;
                                      });
                                      ScaffoldMessenger.of(context).showSnackBar(
                                        SnackBar(content: Text('Habilidad "${s['name']}" ${val ? 'habilitada' : 'deshabilitada'} para tus agentes.')),
                                      );
                                    },
                                  ),
                                );
                              },
                            ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
