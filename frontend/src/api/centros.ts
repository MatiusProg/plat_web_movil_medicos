/** Los centros médicos activos, para elegir en el login y el registro. Es público. */
import { pedir } from './cliente'

export interface Centro {
  slug: string
  name: string
}

export const listarCentros = (senal?: AbortSignal) => pedir<Centro[]>('/accounts/centers/', { senal })
