import { useState } from 'react'
import { Archive, ArchiveRestore, ArrowDown, ArrowUp, EyeOff, Eye, Pencil, Plus } from 'lucide-react'
import { addCompetency, editCompetency, moveCompetency, type CompInput } from '../actions'
import { editablePrograms, nextCode, programCompetencies } from '../domain'
import { useGistar } from '../store'
import type { Competencia } from '../types'
import { Modal } from '../components/Modal'
import { Button, Card, Field, Notice, PageTitle, Segmented, Status, Table, inputCls } from '../ui'

export function CompetencyCatalog() {
  const { data, role, update, toast } = useGistar()
  const programs = editablePrograms(data, role)
  const [programId, setProgramId] = useState(programs[0]?.id ?? '')
  const cohorts = data.cohortes.filter((c) => c.programa_id === programId)
  const [scope, setScope] = useState<string>('programa')
  const [showArchived, setShowArchived] = useState(false)
  const [editing, setEditing] = useState<Competencia | 'new' | null>(null)
  const cohort = scope === 'programa' ? null : cohorts.find((c) => c.id === scope) ?? null
  const all = programCompetencies(data, programId)
  const rows = all.filter((c) => (cohort ? c.cohorte_id === null || c.cohorte_id === cohort.id : c.cohorte_id === null)).filter((c) => showArchived || c.activo)
  const usage = (id: string) => data.evaluaciones.filter((e) => e.competencia_id === id && e.estado === 'publicada').length

  if (!programs.length) return <PageTitle title="Competencias" sub="No tienes programas asignados." />


  return (
    <>
      <PageTitle
        eyebrow="Modelo académico"
        title="Catálogo de competencias"
        sub="Los códigos C1, C2… son identificadores únicos por programa, no una lista cerrada. Las cohortes heredan el catálogo del programa y pueden excluir elementos o añadir competencias propias."
      />
      <Card>
        <div className="mb-5 flex flex-wrap items-end gap-3">
          <Field label="Programa" htmlFor="cat-prog">
            <select
              id="cat-prog"
              className={`${inputCls} w-auto`}
              value={programId}
              onChange={(e) => {
                setProgramId(e.target.value)
                setScope('programa')
              }}
            >
              {programs.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.nombre}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Ámbito">
            <Segmented label="Ámbito" value={scope} onChange={setScope} options={[{ id: 'programa', label: 'Catálogo del programa' }, ...cohorts.map((c) => ({ id: c.id, label: `Cohorte ${c.id}` }))]} />
          </Field>
          <label className="flex items-center gap-2 pb-2.5 text-sm">
            <input type="checkbox" className="size-4 accent-teal" checked={showArchived} onChange={(e) => setShowArchived(e.target.checked)} /> Mostrar archivadas
          </label>
          <Button className="ml-auto" onClick={() => setEditing('new')}>
            <Plus className="size-4" aria-hidden /> {cohort ? 'Competencia específica de cohorte' : 'Nueva competencia'}
          </Button>
        </div>
        {cohort && <Notice>Vista de {cohort.nombre}: las competencias heredadas del programa pueden excluirse solo en esta cohorte; las específicas no afectan a otras cohortes.</Notice>}
        <Table head={['Orden', 'Código', 'Competencia', 'Descriptores N1 · N2 · N3', 'Ámbito', 'Estado', 'Acciones']}>
          {rows.map((c, i) => {
            const excluded = !!cohort && c.cohorte_id === null && cohort.competencias_excluidas.includes(c.id)
            const ids = rows.map((r) => r.id)
            return (
              <tr key={c.id} className={!c.activo || excluded ? 'opacity-60' : ''}>
                <td>
                  <div className="flex gap-0.5">
                    <Button size="sm" variant="subtle" aria-label={`Subir ${c.nombre}`} disabled={i === 0} onClick={() => update((d) => moveCompetency(d, ids, c.id, -1), 'ordenar_competencia', c.id)}>
                      <ArrowUp className="size-3.5" aria-hidden />
                    </Button>
                    <Button size="sm" variant="subtle" aria-label={`Bajar ${c.nombre}`} disabled={i === rows.length - 1} onClick={() => update((d) => moveCompetency(d, ids, c.id, 1), 'ordenar_competencia', c.id)}>
                      <ArrowDown className="size-3.5" aria-hidden />
                    </Button>
                  </div>
                </td>
                <td className="font-mono text-xs font-semibold">{c.codigo}</td>
                <td className="max-w-56">
                  <p className="font-medium">{c.nombre}</p>
                  <p className="line-clamp-2 text-xs text-muted">{c.descripcion}</p>
                </td>
                <td className="max-w-72 text-xs text-muted">
                  {(['1', '2', '3'] as const).map((l) => (
                    <p key={l} className="truncate">
                      <b className="text-ink/70">N{l}</b> {c.niveles[l] || '—'}
                    </p>
                  ))}
                </td>
                <td className="text-xs">{c.cohorte_id ? `Cohorte ${c.cohorte_id}` : cohort ? 'Heredada' : 'Programa'}</td>
                <td>
                  <Status s={excluded ? 'no_admitida' : c.activo ? 'en_seguimiento' : 'borrador'} label={excluded ? 'Excluida aquí' : c.activo ? 'Activa' : 'Archivada'} />
                  <p className="mt-1 text-[11px] text-muted">{usage(c.id)} evaluaciones</p>
                </td>
                <td>
                  <div className="flex flex-wrap gap-1">
                    <Button size="sm" variant="ghost" onClick={() => setEditing(c)} aria-label={`Editar ${c.nombre}`}>
                      <Pencil className="size-3.5" aria-hidden />
                    </Button>
                    {cohort && c.cohorte_id === null ? (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() =>
                          update(
                            (d) => {
                              const coh = d.cohortes.find((x) => x.id === cohort.id)!
                              coh.competencias_excluidas = excluded ? coh.competencias_excluidas.filter((x) => x !== c.id) : [...coh.competencias_excluidas, c.id]
                            },
                            excluded ? 'incluir_competencia_cohorte' : 'excluir_competencia_cohorte',
                            `${cohort.id}/${c.id}`,
                          )
                        }
                      >
                        {excluded ? <Eye className="size-3.5" aria-hidden /> : <EyeOff className="size-3.5" aria-hidden />}
                        {excluded ? 'Incluir' : 'Excluir'}
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => update((d) => (d.competencias.find((x) => x.id === c.id)!.activo = !c.activo), c.activo ? 'archivar_competencia' : 'activar_competencia', c.id)}
                      >
                        {c.activo ? <Archive className="size-3.5" aria-hidden /> : <ArchiveRestore className="size-3.5" aria-hidden />}
                        {c.activo ? 'Archivar' : 'Activar'}
                      </Button>
                    )}
                  </div>
                </td>
              </tr>
            )
          })}
        </Table>
        <p className="mt-4 text-xs text-muted">
          Archivar oculta la competencia de nuevas rúbricas y de la analítica actual, pero conserva su historial de evaluaciones. Próximo código disponible: <b>{nextCode(data, programId)}</b>.
        </p>
      </Card>
      {editing && (
        <CompetencyModal
          comp={editing === 'new' ? null : editing}
          code={editing === 'new' ? nextCode(data, programId) : editing.codigo}
          scopeLabel={cohort ? cohort.nombre : data.programas.find((p) => p.id === programId)?.nombre ?? ''}
          onClose={() => setEditing(null)}
          onSave={(inp) => {
            try {
              const probe = structuredClone(data)
              if (editing === 'new') addCompetency(probe, programId, cohort?.id ?? null, inp)
              else editCompetency(probe, editing.id, inp)
            } catch (e) {
              toast((e as Error).message)
              return false
            }
            update(
              (d) => {
                if (editing === 'new') addCompetency(d, programId, cohort?.id ?? null, inp)
                else editCompetency(d, editing.id, inp)
              },
              editing === 'new' ? 'crear_competencia' : 'editar_competencia',
              programId,
              inp.nombre,
            )
            return true
          }}
        />
      )}
    </>
  )
}

function CompetencyModal({ comp, code, scopeLabel, onClose, onSave }: { comp: Competencia | null; code: string; scopeLabel: string; onClose: () => void; onSave: (i: CompInput) => boolean }) {
  const init: CompInput = { nombre: comp?.nombre ?? '', descripcion: comp?.descripcion ?? '', niveles: comp?.niveles ?? { '1': '', '2': '', '3': '' } }
  const [f, setF] = useState(init)
  const dirty = JSON.stringify(f) !== JSON.stringify(init)
  return (
    <Modal
      open
      size="lg"
      dirty={dirty}
      onClose={onClose}
      title={comp ? `Editar ${comp.codigo} · ${comp.nombre}` : 'Nueva competencia'}
      subtitle={`Ámbito: ${scopeLabel} · Código ${code} (generado, único en el programa)`}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button disabled={!f.nombre.trim()} onClick={() => onSave(f) && onClose()}>
            Guardar
          </Button>
        </>
      }
    >
      <div className="grid gap-4">
        <Field label="Nombre" htmlFor="cm-name">
          <input id="cm-name" data-autofocus className={inputCls} value={f.nombre} onChange={(e) => setF({ ...f, nombre: e.target.value })} />
        </Field>
        <Field label="Descripción" htmlFor="cm-desc">
          <textarea id="cm-desc" className={`${inputCls} min-h-20`} value={f.descripcion} onChange={(e) => setF({ ...f, descripcion: e.target.value })} />
        </Field>
        {(['1', '2', '3'] as const).map((l) => (
          <Field key={l} label={`Descriptor observable · nivel ${l}`} htmlFor={`cm-n${l}`}>
            <input id={`cm-n${l}`} className={inputCls} value={f.niveles[l]} onChange={(e) => setF({ ...f, niveles: { ...f.niveles, [l]: e.target.value } })} />
          </Field>
        ))}
      </div>
    </Modal>
  )
}
