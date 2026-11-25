import type { Schemas } from '../../../shared/api/client'

export type LearnerDelivery = Schemas['EnrollmentDelivery']
export type DeliveryFilter = 'all' | 'outstanding' | 'delivered' | 'reviewed'

export const deliveryStateLabel: Record<LearnerDelivery['state'], string> = {
  pending: 'Pendiente',
  overdue: 'Vencida',
  on_time: 'A tiempo',
  late: 'Con retraso',
}

export function matchesDeliveryFilter(item: LearnerDelivery, filter: DeliveryFilter): boolean {
  switch (filter) {
    case 'outstanding': return item.state === 'pending' || item.state === 'overdue'
    case 'delivered': return item.submission !== null && !item.reviewed
    case 'reviewed': return item.reviewed
    case 'all': return true
  }
}
