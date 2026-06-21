import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/providers.dart';
import '../../theme/app_theme.dart';

class AdsIdeTab extends ConsumerStatefulWidget {
  const AdsIdeTab({super.key});

  @override
  ConsumerState<AdsIdeTab> createState() => _AdsIdeTabState();
}

class _AdsIdeTabState extends ConsumerState<AdsIdeTab> {
  final TextEditingController _promptController = TextEditingController(text: 'Reasignar presupuesto de campañas Meta con ROAS < 1.5 hacia Google Ads');
  List<dynamic> _proposals = [];
  bool _loading = false;
  int _currentStep = 0;

  @override
  void initState() {
    super.initState();
    _loadProposals();
  }

  Future<void> _loadProposals() async {
    setState(() => _loading = true);
    try {
      final client = ref.read(apiClientProvider);
      final res = await client.getCampaignProposals();
      setState(() {
        _proposals = res;
        _currentStep = 0; // Draft
      });
    } catch (e) {
      debugPrint('Failed to load proposals: $e');
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _processProposal(String id, bool approved) async {
    try {
      final client = ref.read(apiClientProvider);
      final res = await client.confirmProposal(id, approved);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Acción confirmada: ${res['detail']}')),
      );
      _loadProposals();
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
    }
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
              const Icon(Icons.campaign, color: AppTheme.primaryColor, size: 28),
              const SizedBox(width: 12),
              Text(
                'IDE de Campañas Publicitarias (SOTA)',
                style: Theme.of(context).textTheme.headlineMedium,
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Ejecución directa mediante API de escritura y control de riesgos de capital.',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppTheme.mutedTextColor),
          ),
          const SizedBox(height: 24),

          // Section 1: Campaign Prompt IDE
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('IDE de Optimización Conversacional', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _promptController,
                    decoration: const InputDecoration(
                      hintText: 'Ej. Pausar AdSets con fatiga creativa alta y reasignar a Google Ads...',
                      prefixIcon: Icon(Icons.keyboard),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      ElevatedButton.icon(
                        onPressed: _loadProposals,
                        icon: const Icon(Icons.rocket_launch),
                        label: const Text('Compilar Propuesta'),
                      ),
                      const SizedBox(width: 12),
                      OutlinedButton(
                        onPressed: () {
                          _promptController.clear();
                        },
                        child: const Text('Limpiar Prompt'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 24),

          // Section 2: Draft-Preview-Confirm Stepper
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Protocolo de Gobierno de Capital: Draft-Preview-Confirm', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 4),
                  const Text(
                    'Los agentes autónomos proponen ajustes financieros, pero la plataforma requiere confirmación manual del operador antes de persistir cambios.',
                    style: TextStyle(fontSize: 12, color: AppTheme.mutedTextColor),
                  ),
                  const SizedBox(height: 20),
                  
                  // Stepper visual indicators
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    children: [
                      _buildStepIndicator(0, '1. Borrador (Draft)'),
                      _buildStepIndicator(1, '2. Previsualizar (Preview)'),
                      _buildStepIndicator(2, '3. Confirmar (Confirm)'),
                    ],
                  ),

                  const SizedBox(height: 24),

                  _loading
                      ? const Center(child: CircularProgressIndicator())
                      : _proposals.isEmpty
                          ? const Center(child: Text('No hay propuestas de optimización activas. Compila una arriba.'))
                          : Column(
                              children: [
                                if (_currentStep == 0) ...[
                                  const Text('Propuestas Generadas en Borrador:', style: TextStyle(fontWeight: FontWeight.bold)),
                                  const SizedBox(height: 12),
                                  ..._proposals.map((p) => _buildProposalTile(p, isDraft: true)),
                                  const SizedBox(height: 16),
                                  ElevatedButton(
                                    onPressed: () => setState(() => _currentStep = 1),
                                    child: const Text('Proceder a Previsualizar'),
                                  ),
                                ] else if (_currentStep == 1) ...[
                                  const Text('Previsualización de Cambios en Presupuesto:', style: TextStyle(fontWeight: FontWeight.bold)),
                                  const SizedBox(height: 12),
                                  ..._proposals.map((p) => _buildProposalTile(p, isDraft: false)),
                                  const SizedBox(height: 16),
                                  Row(
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    children: [
                                      OutlinedButton(
                                        onPressed: () => setState(() => _currentStep = 0),
                                        child: const Text('Volver a Borrador'),
                                      ),
                                      const SizedBox(width: 12),
                                      ElevatedButton(
                                        onPressed: () => setState(() => _currentStep = 2),
                                        child: const Text('Proceder a Confirmar'),
                                      ),
                                    ],
                                  ),
                                ] else if (_currentStep == 2) ...[
                                  const Text('¿Confirmar cambios finales en producción?', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.orange)),
                                  const SizedBox(height: 12),
                                  const Text('Estas acciones modificarán de forma inmediata los presupuestos en Meta y Google Ads.'),
                                  const SizedBox(height: 20),
                                  Row(
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    children: [
                                      ElevatedButton(
                                        onPressed: () {
                                          for (var p in _proposals) {
                                            _processProposal(p['campaign_id'], true);
                                          }
                                        },
                                        style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primaryColor),
                                        child: const Text('Aprobar Todo (Write API)'),
                                      ),
                                      const SizedBox(width: 12),
                                      OutlinedButton(
                                        onPressed: () {
                                          for (var p in _proposals) {
                                            _processProposal(p['campaign_id'], false);
                                          }
                                        },
                                        style: OutlinedButton.styleFrom(foregroundColor: Colors.red, side: const BorderSide(color: Colors.red)),
                                        child: const Text('Rechazar Todo'),
                                      ),
                                    ],
                                  ),
                                ]
                              ],
                            ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStepIndicator(int index, String label) {
    final active = _currentStep == index;
    final passed = _currentStep > index;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: active
            ? AppTheme.primaryColor.withOpacity(0.2)
            : (passed ? AppTheme.secondaryColor.withOpacity(0.1) : Colors.transparent),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: active
              ? AppTheme.primaryColor
              : (passed ? AppTheme.secondaryColor : Colors.white10),
        ),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: active ? AppTheme.primaryColor : (passed ? AppTheme.secondaryColor : AppTheme.mutedTextColor),
          fontWeight: active ? FontWeight.bold : FontWeight.normal,
        ),
      ),
    );
  }

  Widget _buildProposalTile(dynamic p, {required bool isDraft}) {
    return Card(
      color: Colors.black26,
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Row(
          children: [
            Icon(
              p['platform'] == 'meta_ads' ? Icons.facebook : Icons.ads_click,
              color: AppTheme.primaryColor,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('${p['action']} - Campaña ${p['campaign_id']}', style: const TextStyle(fontWeight: FontWeight.bold)),
                  Text(p['description'], style: const TextStyle(fontSize: 12, color: AppTheme.mutedTextColor)),
                ],
              ),
            ),
            if (!isDraft) ...[
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text('Presupuesto: \$${p['current_budget']} -> \$${p['proposed_budget']}', style: const TextStyle(fontSize: 12)),
                  Text('ROAS: ${p['roas']}', style: const TextStyle(fontSize: 10, color: Colors.green)),
                ],
              ),
            ]
          ],
        ),
      ),
    );
  }
}
