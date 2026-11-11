import { GistarProvider } from './gistar/store'
import { Shell } from './gistar/Shell'
import { ApiSessionProvider } from './shared/api/session'

export default function App() {
  return (
    <ApiSessionProvider>
      <GistarProvider>
        <Shell />
      </GistarProvider>
    </ApiSessionProvider>
  )
}
