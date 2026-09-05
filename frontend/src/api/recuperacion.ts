/**
 * US-03 — Recuperación de contraseña (CU3).
 *
 * Los tres endpoints van sin token: quien los usa es justamente alguien que no
 * puede entrar. Lo que sí viaja siempre es el **slug de la organización**, y no
 * es opcional: el correo es único por inquilino, no de forma global, y sin él
 * el backend no sabe en qué centro médico buscar.
 *
 * Los tipos viven acá y no en `api/tipos.ts` por la regla del archivo
 * compartido: ese archivo es el contrato común de `accounts` y cada historia
 * trae su propio módulo.
 */

import { pedir, type Contexto } from './cliente'

export interface SolicitudRecuperacion {
  organization: string
  email: string
}

/**
 * La respuesta de la solicitud es **siempre la misma**, exista o no la cuenta.
 * La pantalla no puede —ni debe— distinguir un caso del otro: si pudiera, el
 * formulario serviría para averiguar qué correos están registrados en cada
 * centro médico.
 */
export interface RecuperacionSolicitada {
  detail: string
}

export interface EnlaceValido {
  valid: true
  /** Enmascarado: `a**@kolping.test`. Alcanza para reconocer la cuenta propia. */
  email: string
  expires_at: string
}

export interface ContrasenaCambiada {
  detail: string
}

export function solicitarRecuperacion(
  datos: SolicitudRecuperacion,
  senal?: AbortSignal,
): Promise<RecuperacionSolicitada> {
  return pedir<RecuperacionSolicitada>('/accounts/password-reset/', {
    metodo: 'POST',
    cuerpo: datos,
    senal,
  })
}

/**
 * Comprueba el enlace antes de mostrar el formulario.
 *
 * Existe para no hacerle escribir a alguien una contraseña nueva dos veces
 * para recién entonces enterarse de que el enlace venció.
 */
export function verificarEnlace(
  organizacion: string,
  token: string,
  senal?: AbortSignal,
): Promise<EnlaceValido> {
  return pedir<EnlaceValido>('/accounts/password-reset/verify/', {
    metodo: 'POST',
    cuerpo: { organization: organizacion, token },
    senal,
  })
}

export function confirmarRecuperacion(
  organizacion: string,
  token: string,
  password: string,
  passwordConfirmacion: string,
  senal?: AbortSignal,
): Promise<ContrasenaCambiada> {
  return pedir<ContrasenaCambiada>('/accounts/password-reset/confirm/', {
    metodo: 'POST',
    cuerpo: {
      organization: organizacion,
      token,
      password,
      password_confirmation: passwordConfirmacion,
    },
    senal,
  })
}

/** El contexto no se usa acá: ninguno de los tres endpoints lleva token. */
export type SinSesion = Contexto
