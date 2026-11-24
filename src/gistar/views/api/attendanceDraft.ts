import type { Schemas } from '../../../shared/api/client'

/** Always create a fresh draft when selecting a different persisted record. */
export function attendanceDraft(record?: Schemas['RecordOut']) {
  return {
    status: record?.status ?? 'presente',
    modality: record?.modality ?? 'presencial',
    justification: record?.justification ?? 'no_justificada',
    reason: '',
  } as const
}
