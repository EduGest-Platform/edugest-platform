import { expect, it } from 'vitest'
import { deliveryStateLabel, matchesDeliveryFilter, type LearnerDelivery } from '../views/api/learnerDeliveryStates'

const activity: LearnerDelivery = {
  assignment_id: 'synthetic-assignment',
  title: 'Actividad sintética',
  due_at: '2026-11-25T08:00:00Z',
  state: 'pending',
  reviewed: false,
  submission: null,
}

it('keeps pending and overdue work under outstanding, with different labels', () => {
  expect(matchesDeliveryFilter(activity, 'outstanding')).toBe(true)
  expect(matchesDeliveryFilter({ ...activity, state: 'overdue' }, 'outstanding')).toBe(true)
  expect(deliveryStateLabel.pending).toBe('Pendiente')
  expect(deliveryStateLabel.overdue).toBe('Vencida')
  expect(matchesDeliveryFilter(activity, 'delivered')).toBe(false)
})

it('separates recorded submissions from reviewed submissions', () => {
  const submission: NonNullable<LearnerDelivery['submission']> = {
    id: 'synthetic-submission', assignment_id: activity.assignment_id, enrollment_id: 'synthetic-enrollment',
    portfolio_url: null, check_results: null, status: 'submitted', revision: 1, late: false,
    first_submitted_at: activity.due_at, submitted_at: activity.due_at, reviewed_at: null,
  }
  const delivered: LearnerDelivery = { ...activity, state: 'on_time', submission }
  const reviewed = { ...delivered, reviewed: true }
  expect(matchesDeliveryFilter(delivered, 'delivered')).toBe(true)
  expect(matchesDeliveryFilter(delivered, 'reviewed')).toBe(false)
  expect(matchesDeliveryFilter(reviewed, 'delivered')).toBe(false)
  expect(matchesDeliveryFilter(reviewed, 'reviewed')).toBe(true)
  expect(matchesDeliveryFilter(reviewed, 'all')).toBe(true)
})
