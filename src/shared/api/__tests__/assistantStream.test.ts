import { describe, expect, it, vi } from 'vitest'
import { readAssistantStream } from '../assistantStream'

const encoder = new TextEncoder()

describe('assistant SSE reader', () => {
  it('dispatches progress before the answer, even with split UTF-8 and CRLF frames', async () => {
    let writer!: ReadableStreamDefaultController<Uint8Array>
    const stream = new ReadableStream<Uint8Array>({ start: controller => { writer = controller } })
    const onPhase = vi.fn()
    const onDelta = vi.fn()
    const answer = readAssistantStream(stream, { onPhase, onDelta })
    const progress = encoder.encode('event: phase\r\ndata: {"source_kind":"documents"}\r\n\r\n'
      + 'event: delta\r\ndata: {"text":"sí"}\r\n\r\n')
    for (const byte of progress) writer.enqueue(Uint8Array.of(byte))
    await vi.waitFor(() => expect(onDelta).toHaveBeenCalledWith('sí'))
    expect(onPhase).toHaveBeenCalledWith('documents')

    writer.enqueue(encoder.encode('event: answer\ndata: {"answer":"sí","status":"answered","source_kind":"documents","mode":"extractive","retrieval":"keyword","as_of":"2026-11-26","citations":[],"scope_cohorts":[]}\n\n'))
    await expect(answer).resolves.toMatchObject({ answer: 'sí', status: 'answered' })
  })

  it('rejects a connection that closes without a terminal answer', async () => {
    const stream = new ReadableStream<Uint8Array>({ start(controller) {
      controller.enqueue(encoder.encode('event: delta\ndata: {"text":"Incompleta"}\n\n'))
      controller.close()
    } })
    await expect(readAssistantStream(stream, { onPhase: vi.fn(), onDelta: vi.fn() }))
      .rejects.toThrow('respuesta completa')
  })
})


it.each(['not-json', 'null', '{}', '{"answer":"sí","status":"answered"}', '{"answer":"sí","status":"unknown"}'])('rejects invalid terminal payload %s and releases the reader', async payload => {
  const cancel = vi.fn()
  const stream = new ReadableStream<Uint8Array>({
    start(controller) { controller.enqueue(encoder.encode('event: answer\ndata: ' + payload + '\n\n')) },
    cancel,
  })
  await expect(readAssistantStream(stream, { onPhase: vi.fn(), onDelta: vi.fn() })).rejects.toThrow('no es válida')
  expect(cancel).toHaveBeenCalled()
  expect(stream.locked).toBe(false)
})


it('ignores unknown events and rejects server errors without leaking their payload', async () => {
  const cancel = vi.fn()
  const onDelta = vi.fn()
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(encoder.encode('event: extension\ndata: not-json\n\nevent: delta\ndata: {"text":"partial"}\n\nevent: error\ndata: {"detail":"private-provider-detail"}\n\n'))
    },
    cancel,
  })
  await expect(readAssistantStream(stream, { onPhase: vi.fn(), onDelta })).rejects.not.toThrow('private-provider-detail')
  expect(onDelta).toHaveBeenCalledWith('partial')
  expect(cancel).toHaveBeenCalled()
  expect(stream.locked).toBe(false)
})
