import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/providers.dart';
import '../../theme/app_theme.dart';

class WhiteLabelTab extends ConsumerStatefulWidget {
  const WhiteLabelTab({super.key});

  @override
  ConsumerState<WhiteLabelTab> createState() => _WhiteLabelTabState();
}

class _WhiteLabelTabState extends ConsumerState<WhiteLabelTab> {
  final TextEditingController _cnameController = TextEditingController(text: 'portal.clientedeagencia.com');
  final TextEditingController _smtpServerController = TextEditingController(text: 'smtp.clientedeagencia.com');
  final TextEditingController _smtpUserController = TextEditingController(text: 'reportes@clientedeagencia.com');
  final TextEditingController _smtpPassController = TextEditingController(text: '••••••••••••••••');

  bool _serverSyncActive = true;
  String _activeTemplate = 'Master Premium Dashboard';

  // Locks map to selectively lock elements from global updates
  final Map<String, bool> _elementLocks = {
    'Estilos de Identidad Visual': true,
    'Estructura de Barra Lateral': false,
    'Configuración de Gateways de Pago': true,
    'Reglas de Optimización de Presupuesto': false,
  };

  @override
  void initState() {
    super.initState();
    _cnameController.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    _cnameController.dispose();
    super.dispose();
  }

  Widget _buildPortalPreview() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Vista Previa en Vivo del Portal del Cliente', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const Text('Representación visual de cómo verán los clientes el dashboard bajo tu marca blanca.', style: TextStyle(fontSize: 12, color: AppTheme.mutedTextColor)),
            const SizedBox(height: 16),
            Container(
              height: 190,
              width: double.infinity,
              decoration: BoxDecoration(
                color: Colors.black45,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppTheme.secondaryColor, width: 1.5),
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(10),
                child: Column(
                  children: [
                    // Mock Browser Bar
                    Container(
                      color: Colors.black.withOpacity(0.85),
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      child: Row(
                        children: [
                          const Icon(Icons.circle, color: AppTheme.neonGreen, size: 8),
                          const SizedBox(width: 8),
                          Text(
                            _cnameController.text.isEmpty ? 'portal.tuagencia.com' : _cnameController.text,
                            style: const TextStyle(fontSize: 11, fontFamily: 'monospace', color: Colors.white70),
                          ),
                        ],
                      ),
                    ),
                    // Mock Dashboard Contents
                    Expanded(
                      child: Container(
                        color: AppTheme.backgroundColor,
                        padding: const EdgeInsets.all(12.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                const Text('INFORME CORPORATIVO', style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Colors.white)),
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                  decoration: BoxDecoration(
                                    color: AppTheme.secondaryColor.withOpacity(0.2),
                                    borderRadius: BorderRadius.circular(4),
                                  ),
                                  child: const Text('MARCA BLANCA', style: TextStyle(fontSize: 8, color: AppTheme.secondaryColor, fontWeight: FontWeight.bold)),
                                ),
                              ],
                            ),
                            const SizedBox(height: 10),
                            Row(
                              children: [
                                Expanded(child: _buildMiniCard('Conversiones', '9.4k', AppTheme.neonBlue)),
                                const SizedBox(width: 8),
                                Expanded(child: _buildMiniCard('ROAS Promedio', '4.2x', AppTheme.neonGreen)),
                              ],
                            ),
                            const Spacer(),
                            const Text(
                              'Sincronizado vía SMTP Gateway: Conectado',
                              style: TextStyle(fontSize: 9, color: AppTheme.mutedTextColor),
                            ),
                          ],
                        ),
                      ),
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

  Widget _buildMiniCard(String title, String val, Color c) {
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: Colors.white12,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: Colors.white10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(fontSize: 8, color: AppTheme.mutedTextColor)),
          Text(val, style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: c)),
        ],
      ),
    );
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
              const Icon(Icons.palette, color: AppTheme.secondaryColor, size: 28),
              const SizedBox(width: 12),
              Text(
                'Marca Blanca & Gobernanza de Datos',
                style: Theme.of(context).textTheme.headlineMedium,
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Personalización visual de portales para clientes, SMTP gateways y sincronización centralizada de instancias (Server Sync).',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppTheme.mutedTextColor),
          ),
          const SizedBox(height: 24),

          // Section 1: CNAME Mapping & Live Preview
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Asignación de Dominio Personalizado (CNAME)', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  const Text('Permite que tus clientes accedan a sus informes desde tu propio subdominio corporativo.', style: TextStyle(fontSize: 12, color: AppTheme.mutedTextColor)),
                  const SizedBox(height: 16),
                  TextField(
                    controller: _cnameController,
                    decoration: const InputDecoration(
                      labelText: 'Subdominio CNAME Mapeado',
                      prefixIcon: Icon(Icons.dns),
                      suffixIcon: Icon(Icons.check_circle, color: AppTheme.secondaryColor),
                    ),
                  ),
                  const SizedBox(height: 16),
                  ElevatedButton(
                    onPressed: () {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Dominio CNAME configurado y validado en DNS.')),
                      );
                    },
                    child: const Text('Validar y Guardar Dominio'),
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 24),
          _buildPortalPreview(),
          const SizedBox(height: 24),

          // Section 2: SMTP Config
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Gateway SMTP Personalizado', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  const Text('Envía alertas e informes PDF automatizados utilizando el correo corporativo de la agencia.', style: TextStyle(fontSize: 12, color: AppTheme.mutedTextColor)),
                  const SizedBox(height: 16),
                  TextField(
                    controller: _smtpServerController,
                    decoration: const InputDecoration(
                      labelText: 'Servidor SMTP',
                      prefixIcon: Icon(Icons.mail),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _smtpUserController,
                          decoration: const InputDecoration(
                            labelText: 'Usuario SMTP',
                            prefixIcon: Icon(Icons.person),
                          ),
                        ),
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: TextField(
                          controller: _smtpPassController,
                          obscureText: true,
                          decoration: const InputDecoration(
                            labelText: 'Contraseña SMTP',
                            prefixIcon: Icon(Icons.lock),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  ElevatedButton.icon(
                    onPressed: () {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Guardado SMTP completado. Correo de prueba enviado.')),
                      );
                    },
                    icon: const Icon(Icons.send),
                    label: const Text('Guardar y Probar Conexión'),
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 24),

          // Section 3: Server Sync & Granular Locks
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Consola Central y Server Sync', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  const Text('Propaga instantáneamente las actualizaciones estructurales de widgets a todos los portales de clientes.', style: TextStyle(fontSize: 12, color: AppTheme.mutedTextColor)),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      const Text('Plantilla Maestra Activa: ', style: TextStyle(fontWeight: FontWeight.bold)),
                      const SizedBox(width: 8),
                      Text(_activeTemplate, style: const TextStyle(color: AppTheme.secondaryColor)),
                    ],
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'Bloquear elementos individuales de actualizaciones maestras:',
                    style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  ..._elementLocks.keys.map((key) {
                    return CheckboxListTile(
                      dense: true,
                      title: Text(key, style: const TextStyle(fontSize: 12)),
                      subtitle: Text(
                        _elementLocks[key]! ? 'Bloqueado (No se actualizará globalmente)' : 'Sincronizado',
                        style: const TextStyle(fontSize: 10),
                      ),
                      value: _elementLocks[key],
                      onChanged: (val) {
                        setState(() {
                          _elementLocks[key] = val ?? false;
                        });
                      },
                    );
                  }),
                  const Divider(color: Colors.white10),
                  Row(
                    children: [
                      const Text('Sincronización Automática de Servidores'),
                      const Spacer(),
                      Switch(
                        value: _serverSyncActive,
                        onChanged: (val) {
                          setState(() => _serverSyncActive = val);
                        },
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  ElevatedButton.icon(
                    onPressed: () {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Server Sync completado. 12 instancias de clientes actualizadas.')),
                      );
                    },
                    icon: const Icon(Icons.cloud_sync),
                    label: const Text('Propagar Cambios Ahora'),
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
