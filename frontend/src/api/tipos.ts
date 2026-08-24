/**
 * El contrato con el backend, tal como lo devuelve `accounts`.
 *
 * Los nombres de los campos van en inglés porque son los del backend, que
 * sigue la nomenclatura HL7 FHIR (docs/convenciones-de-codigo.md §3). Cambiarlos
 * acá obligaría a traducir en cada petición y a mantener dos vocabularios.
 */

export interface Rol {
  code: string
  name: string
}

export interface UsuarioSesion {
  id: string
  email: string
  full_name: string
  document_type: string
  document_number: string
  /** El slug del centro médico. `null` sólo para el Superadministrador. */
  organization: string | null
  is_platform_admin: boolean
  roles: Rol[]
  /** Códigos `modulo.recurso.accion`. Es lo que decide qué se ve en el menú. */
  permissions: string[]
}

export interface SesionIniciada {
  access: string
  refresh: string
  user: UsuarioSesion
}

/**
 * Los códigos de error del backend. Se compara contra esto y nunca contra el
 * texto del mensaje: el texto puede cambiar, el código es el contrato.
 */
export type CodigoError =
  | 'credenciales_invalidas'
  | 'cuenta_bloqueada'
  | 'cuenta_inactiva'
  | 'organizacion_no_disponible'
  | 'refresh_invalido'
  | 'refresh_ajeno'
  | 'token_sin_organizacion'
  | 'sin_conexion'
  | 'desconocido'

export class ErrorApi extends Error {
  readonly codigo: CodigoError
  readonly estado: number
  /** Sólo en `cuenta_bloqueada`: cuándo vence el bloqueo, en ISO 8601. */
  readonly bloqueadaHasta?: string
  /** Errores por campo, cuando el backend responde una validación de forma. */
  readonly porCampo?: Record<string, string[]>

  constructor(
    mensaje: string,
    codigo: CodigoError,
    estado: number,
    extra?: { bloqueadaHasta?: string; porCampo?: Record<string, string[]> },
  ) {
    super(mensaje)
    this.name = 'ErrorApi'
    this.codigo = codigo
    this.estado = estado
    this.bloqueadaHasta = extra?.bloqueadaHasta
    this.porCampo = extra?.porCampo
  }
}
