import { useId, useState, type FormEvent } from 'react'
import type { Schemas } from '../../../shared/api/client'
import { Button, Field, inputCls } from '../../ui'

type Draft = Schemas['CompetencyWrite']
const fields = [
  ['codigo', 'Código', 3], ['nombre', 'Nombre', 160], ['descripcion', 'Descripción', 2000],
  ['level_1', 'Nivel 1', 2000], ['level_2', 'Nivel 2', 2000], ['level_3', 'Nivel 3', 2000],
] as const

function blank(code: string): Draft {
  return { codigo: code, nombre: '', descripcion: '', level_1: '', level_2: '', level_3: '' }
}

export function CompetencyFrameworkEditor({ draft, busy, onSave, onClose }: {
  draft: Schemas['FrameworkOut'] | null
  busy: boolean
  onSave: (body: Schemas['FrameworkWrite']) => void
  onClose: () => void
}) {
  const prefix = useId()
  const [rows, setRows] = useState(() => draft ? draft.competencies.map(item => ({
    codigo: item.codigo, nombre: item.nombre, descripcion: item.descripcion,
    level_1: item.level_1, level_2: item.level_2, level_3: item.level_3,
  })) : [blank('C1')])

  const codes = rows.map(row => row.codigo.trim())
  const duplicateCodes = [...new Set(codes.filter((code, index) => code && codes.indexOf(code) !== index))]

  function submit(event: FormEvent) {
    event.preventDefault()
    if (busy || duplicateCodes.length) return
    onSave({ competencies: rows })
  }

  return (
    <form className="grid gap-3" onSubmit={submit}>
      <h3 className="font-semibold">{draft ? `Editar borrador v${draft.version}` : 'Nuevo borrador'}</h3>
      <fieldset disabled={busy} className="grid min-w-0 gap-4">
        {rows.map((row, index) => (
          <fieldset key={index} className="grid min-w-0 gap-3 rounded-xl border border-line p-3 sm:grid-cols-2">
            <legend className="px-1 text-sm font-medium">Competencia {index + 1}</legend>
            {fields.map(([field, label, max]) => {
              const id = `${prefix}-${index}-${field}`
              const update = (value: string) => setRows(previous =>
                previous.map((item, position) => position === index ? { ...item, [field]: value } : item))
              return (
                <Field key={field} label={label} htmlFor={id}>
                  {field === 'codigo' || field === 'nombre'
                    ? <input id={id} className={inputCls} value={row[field]} required maxLength={max}
                        pattern={field === 'codigo' ? 'C[1-9][0-9]?' : undefined} onChange={event => update(event.target.value)} />
                    : <textarea id={id} className={inputCls} value={row[field] ?? ''} required={field !== 'descripcion'}
                        rows={2} maxLength={max} onChange={event => update(event.target.value)} />}
                </Field>
              )
            })}
            {rows.length > 1 && <Button variant="ghost" onClick={() => setRows(previous => previous.filter((_, i) => i !== index))}>
              Quitar competencia {index + 1}
            </Button>}
          </fieldset>
        ))}
        {duplicateCodes.length > 0 && <p role="alert" className="rounded-lg border border-line p-3 text-sm">Los códigos de competencia deben ser únicos. Revisa: {duplicateCodes.join(", ")}.</p>}
        <div className="flex flex-wrap gap-2">
          <Button variant="ghost" disabled={rows.length >= 30} onClick={() => setRows(previous => [...previous, blank('')])}>Añadir competencia</Button>
          <Button type="submit" disabled={duplicateCodes.length > 0}>{busy ? 'Guardando…' : 'Guardar borrador'}</Button>
          <Button variant="ghost" onClick={onClose}>Cancelar edición</Button>
        </div>
      </fieldset>
    </form>
  )
}
