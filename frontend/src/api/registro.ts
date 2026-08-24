import { pedir } from './cliente'

export interface RegistroPacienteDatos {
  organization: string
  email: string
  password: string
  password_confirmation: string
  document_number: string
  first_name: string
  last_name: string
  document_type?: 'CI' | 'PAS' | 'NIT' | 'OTRO'
  phone?: string
  birth_date?: string | null
  sex?: 'M' | 'F' | 'X' | null
}

export interface RegistroPacienteRespuesta {
  id: string
  email: string
  organization: string
  role: string
  patient_id: string
}

export function registrarPaciente(
  datos: RegistroPacienteDatos,
  senal?: AbortSignal,
): Promise<RegistroPacienteRespuesta> {
  return pedir<RegistroPacienteRespuesta>('/accounts/register/', {
    metodo: 'POST',
    cuerpo: datos,
    senal,
  })
}
