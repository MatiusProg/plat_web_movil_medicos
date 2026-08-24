/**
 * El lado izquierdo de la pantalla de inicio de sesión.
 *
 * No es decoración: en una plataforma multi-inquilino la primera pregunta de
 * quien entra es "¿estoy en el centro médico correcto?". Este panel contesta
 * eso antes de que escriba nada.
 *
 * En pantallas chicas se colapsa a una franja compacta —el formulario es lo
 * que importa en un teléfono— pero no desaparece, para no perder esa respuesta.
 */

import { IconoEscudo, IconoPulso } from './iconos'

export function PanelMarca({ organizacion }: { organizacion?: string }) {
  return (
    <aside className="malla-marca relative flex flex-col justify-between overflow-hidden p-8 text-white lg:p-12">
      <div className="reticula pointer-events-none absolute inset-0" aria-hidden="true" />

      {/* --- Identidad --- */}
      <div className="relative">
        <div className="flex items-center gap-3">
          <span className="grid size-10 place-items-center rounded-xl bg-white/15 ring-1 ring-white/25 backdrop-blur-sm">
            <IconoPulso className="size-5.5" />
          </span>
          <div className="leading-tight">
            <p className="text-[0.9375rem] font-semibold">Centro Médico</p>
            <p className="text-xs text-white/70">Plataforma de atención ambulatoria</p>
          </div>
        </div>
      </div>

      {/* --- Mensaje. Sólo en pantallas grandes: en un teléfono, entre el
             mensaje y el formulario, gana el formulario. --- */}
      <div className="relative hidden max-w-md lg:block">
        <h2 className="text-[2rem] leading-[1.15] font-semibold tracking-tight text-balance">
          La historia clínica de cada paciente, en un solo lugar.
        </h2>
        <p className="mt-4 text-[0.9375rem] leading-relaxed text-pretty text-white/75">
          Agendá fichas, registrá consultas y consultá antecedentes desde
          cualquiera de las sucursales, con la información siempre al día.
        </p>

        <ul className="mt-8 space-y-3 text-sm text-white/80">
          {[
            'Agenda y fichas en línea',
            'Historia clínica digital compartida entre sucursales',
            'Acceso diferenciado según el rol de cada persona',
          ].map((punto) => (
            <li key={punto} className="flex items-start gap-2.5">
              <IconoEscudo className="mt-px size-4.5 shrink-0 text-white/50" />
              <span>{punto}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* --- Pie: qué centro médico es --- */}
      <div className="relative">
        {organizacion ? (
          <p className="text-sm text-white/70">
            Ingresando a{' '}
            <span className="font-medium text-white">{organizacion}</span>
          </p>
        ) : (
          <p className="text-sm text-white/55">
            Cada centro médico administra su propia información.
          </p>
        )}
      </div>
    </aside>
  )
}
