/// Fechas de las fichas en el formato que lee un paciente: "lun 06/10 · 09:00".
///
/// Sin `intl` a propósito: la aplicación no lo usa en ningún otro lado, y
/// sumarlo sólo para los nombres de los días es más dependencia que problema.
library;

const _dias = ['lun', 'mar', 'mié', 'jue', 'vie', 'sáb', 'dom'];

String _dos(int n) => n.toString().padLeft(2, '0');

String hora(DateTime fecha) => '${_dos(fecha.hour)}:${_dos(fecha.minute)}';

String fecha(DateTime fecha) =>
    '${_dias[fecha.weekday - 1]} ${_dos(fecha.day)}/${_dos(fecha.month)}/${fecha.year}';

String fechaHora(DateTime valor) => '${fecha(valor)} · ${hora(valor)}';
