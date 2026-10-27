import { pedir, type Contexto } from './cliente'
import type { Ficha, ReservarFichaDatos } from './fichas'

export function reservarEnMostrador(datos: ReservarFichaDatos, contexto: Contexto): Promise<Ficha> {
  return pedir<Ficha>('/appointments/counter/book/', {
    ...contexto, metodo: 'POST', cuerpo: {
      patient: datos.patient, practitioner: datos.practitioner,
      branch: datos.branch, schedule: datos.schedule, starts_at: datos.startsAt,
    },
  })
}

export interface CobroMostrador {
  payment_id: string
  provider: 'cash'
  amount: string
  currency: string
  status: 'succeeded'
  appointment: Ficha
}

export function cobrarEnMostrador(id: string, contexto: Contexto): Promise<CobroMostrador> {
  return pedir<CobroMostrador>(`/payments/appointments/${id}/cash/`, {
    ...contexto, metodo: 'POST',
  })
}
