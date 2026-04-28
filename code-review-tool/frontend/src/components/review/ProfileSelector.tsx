import type { ProfileId, ReviewProfile } from '../../types'

const ICONS: Record<ProfileId, string> = {
  general: '⚖️',
  security: '🔒',
  performance: '⚡',
  style: '✨',
}

interface Props {
  profiles: ReviewProfile[]
  selected: ProfileId
  onSelect: (id: ProfileId) => void
  disabled?: boolean
}

export function ProfileSelector({ profiles, selected, onSelect, disabled }: Props) {
  const selectedProfile = profiles.find(p => p.id === selected)

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1.5" role="group" aria-label="Review profile">
        {profiles.map(profile => (
          <button
            key={profile.id}
            type="button"
            aria-pressed={profile.id === selected ? 'true' : 'false'}
            disabled={disabled}
            onClick={() => {
              if (profile.id !== selected) onSelect(profile.id)
            }}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${
              profile.id === selected
                ? 'bg-brand-600 text-white shadow-sm'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            <span aria-hidden>{ICONS[profile.id as ProfileId] ?? ''}</span>
            {profile.name}
          </button>
        ))}
      </div>

      {selectedProfile && (
        <p className="text-xs text-gray-500 italic">{selectedProfile.description}</p>
      )}
    </div>
  )
}
