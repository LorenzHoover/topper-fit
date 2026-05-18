// Server Component (no 'use client') — this is fine because it just renders
// the FitmentSearch component. All the interactivity lives inside that component.
import FitmentSearch from './components/FitmentSearch'

export default function Home() {
  return <FitmentSearch />
}
