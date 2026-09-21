import Tabs from '../ui/Tabs'

export default function NotesTabs({ tabs, active, onChange }) {
  return <Tabs tabs={tabs} active={active} onChange={onChange} className="mb-4" idPrefix="notes-tab" />
}
