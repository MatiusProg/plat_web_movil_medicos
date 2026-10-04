import { pedir, type Contexto } from './cliente'

// =========================================================
// US-07 — OPCIONES DE PACIENTE PARA RESERVA
// =========================================================

export interface OpcionDePaciente {
  id: string
  full_name: string
  relationship: string
  relationship_label: string
  is_self: boolean
  birth_date: string | null
}

export function listarOpcionesDePaciente(
    contexto: Contexto,
    senal?: AbortSignal,
): Promise<OpcionDePaciente[]> {
  return pedir<OpcionDePaciente[]>(
      '/patients/dependents/patient-options/',
      { ...contexto, senal },
  )
}

// =========================================================
// US-09 — BÚSQUEDA Y CONSULTA DE PACIENTES
// =========================================================

export interface PacienteResumen {
  id: string
  first_name: string
  last_name: string
  full_name: string
  document_type: string
  document_number: string | null
  birth_date: string | null
  phone: string
  is_active: boolean
}

export interface ProximaFichaPaciente {
  id: string
  branch: string
  branch_name: string
  practitioner: string
  practitioner_name: string
  starts_at: string
  ends_at: string
  status: string
  status_label: string
}

export interface PacienteDetalle extends PacienteResumen {
  sex: string
  created_at: string
  updated_at: string
  upcoming_appointments: ProximaFichaPaciente[]
}

export interface PaginaPacientes {
  count: number
  next: string | null
  previous: string | null
  results: PacienteResumen[]
}

export interface BuscarPacientesFiltros {
  q?: string
  document?: string
  status?: 'active' | 'inactive' | ''
  branch?: string
  page?: number
  pageSize?: number
}

export function buscarPacientes(
    filtros: BuscarPacientesFiltros,
    contexto: Contexto,
    senal?: AbortSignal,
): Promise<PaginaPacientes> {
  const parametros = new URLSearchParams()

  if (filtros.q?.trim()) {
    parametros.set('q', filtros.q.trim())
  }

  if (filtros.document?.trim()) {
    parametros.set(
        'document',
        filtros.document.trim(),
    )
  }

  if (filtros.status) {
    parametros.set(
        'status',
        filtros.status,
    )
  }

  if (filtros.branch?.trim()) {
    parametros.set(
        'branch',
        filtros.branch.trim(),
    )
  }

  if (filtros.page) {
    parametros.set(
        'page',
        String(filtros.page),
    )
  }

  if (filtros.pageSize) {
    parametros.set(
        'page_size',
        String(filtros.pageSize),
    )
  }

  const consulta =
      parametros.toString()

  return pedir<PaginaPacientes>(
      `/patients/search/${consulta ? `?${consulta}` : ''}`,
      {
        ...contexto,
        senal,
      },
  )
}

export function obtenerPaciente(
    id: string,
    contexto: Contexto,
    senal?: AbortSignal,
): Promise<PacienteDetalle> {
  return pedir<PacienteDetalle>(
      `/patients/search/${id}/`,
      {
        ...contexto,
        senal,
      },
  )
}

// =========================================================
// US-10 — ABM DE PACIENTES
// =========================================================

export interface PacienteGuardar {
  document_type: string
  document_number: string | null
  first_name: string
  last_name: string
  birth_date: string | null
  sex: string
  phone: string
}

export interface PacienteAdministrado
    extends PacienteResumen {
  sex: string
  created_at: string
  updated_at: string
}

export function crearPaciente(
    datos: PacienteGuardar,
    contexto: Contexto,
): Promise<PacienteAdministrado> {
  return pedir<PacienteAdministrado>(
      '/patients/admin/',
      {
        ...contexto,
        metodo: 'POST',
        cuerpo: datos,
      },
  )
}

export function editarPaciente(
    id: string,
    datos: Partial<PacienteGuardar>,
    contexto: Contexto,
): Promise<PacienteAdministrado> {
  return pedir<PacienteAdministrado>(
      `/patients/admin/${id}/`,
      {
        ...contexto,
        metodo: 'PATCH',
        cuerpo: datos,
      },
  )
}

export function desactivarPaciente(
    id: string,
    contexto: Contexto,
): Promise<void> {
  return pedir<void>(
      `/patients/admin/${id}/`,
      {
        ...contexto,
        metodo: 'DELETE',
      },
  )
}

export interface FusionarPacientesDatos {
  source_patient: string
  target_patient: string
}

export function fusionarPacientes(
    datos: FusionarPacientesDatos,
    contexto: Contexto,
): Promise<PacienteAdministrado> {
  return pedir<PacienteAdministrado>(
      '/patients/admin/merge/',
      {
        ...contexto,
        metodo: 'POST',
        cuerpo: datos,
      },
  )
}