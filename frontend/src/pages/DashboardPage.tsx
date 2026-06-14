import type { EstadoMinuta } from '../types/domain'

export default function DashboardPage({ estado }: { estado: EstadoMinuta }) {
  return <div>Dashboard: {estado}</div>
}
