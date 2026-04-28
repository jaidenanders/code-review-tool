import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { FileTree } from '../components/repos/FileTree'
import { mockFileTree } from './fixtures'

describe('FileTree — multi-select mode', () => {
  it('shows checkboxes when multiSelect is true', () => {
    render(
      <FileTree
        items={mockFileTree}
        onSelectFile={vi.fn()}
        multiSelect
        selectedPaths={[]}
        onSelectionChange={vi.fn()}
      />,
    )
    const checkboxes = screen.getAllByRole('checkbox')
    // Only blobs get checkboxes, not directories
    expect(checkboxes.length).toBeGreaterThan(0)
  })

  it('does not show checkboxes in single-select mode', () => {
    render(<FileTree items={mockFileTree} onSelectFile={vi.fn()} />)
    expect(screen.queryAllByRole('checkbox')).toHaveLength(0)
  })

  it('calls onSelectionChange when checkbox is clicked', async () => {
    const onSelectionChange = vi.fn()
    const user = userEvent.setup()
    render(
      <FileTree
        items={mockFileTree}
        onSelectFile={vi.fn()}
        multiSelect
        selectedPaths={[]}
        onSelectionChange={onSelectionChange}
      />,
    )
    const checkboxes = screen.getAllByRole('checkbox')
    await user.click(checkboxes[0])
    expect(onSelectionChange).toHaveBeenCalled()
  })

  it('checkbox is checked for paths in selectedPaths', () => {
    render(
      <FileTree
        items={mockFileTree}
        onSelectFile={vi.fn()}
        multiSelect
        selectedPaths={['src/index.ts']}
        onSelectionChange={vi.fn()}
      />,
    )
    const indexCheckbox = screen.getByRole('checkbox', { name: /index\.ts/i })
    expect(indexCheckbox).toBeChecked()
  })

  it('can select multiple files', async () => {
    const selections: string[][] = []
    const onSelectionChange = (paths: string[]) => selections.push(paths)
    const user = userEvent.setup()

    const { rerender } = render(
      <FileTree
        items={mockFileTree}
        onSelectFile={vi.fn()}
        multiSelect
        selectedPaths={[]}
        onSelectionChange={onSelectionChange}
      />,
    )
    const checkboxes = screen.getAllByRole('checkbox')
    await user.click(checkboxes[0])

    // Simulate parent updating selectedPaths
    rerender(
      <FileTree
        items={mockFileTree}
        onSelectFile={vi.fn()}
        multiSelect
        selectedPaths={selections[0] ?? []}
        onSelectionChange={onSelectionChange}
      />,
    )
    await user.click(checkboxes[1])

    expect(selections.length).toBeGreaterThan(0)
  })

  it('directories cannot be checked', () => {
    render(
      <FileTree
        items={mockFileTree}
        onSelectFile={vi.fn()}
        multiSelect
        selectedPaths={[]}
        onSelectionChange={vi.fn()}
      />,
    )
    // 'src' is a directory — no checkbox for it
    const folderItem = screen.getByText('src').closest('li')
    const checkbox = folderItem?.querySelector('input[type="checkbox"]')
    expect(checkbox).toBeNull()
  })

  it('clicking unchecked file adds it to selection', async () => {
    let selected: string[] = []
    const user = userEvent.setup()

    const { rerender } = render(
      <FileTree
        items={mockFileTree}
        onSelectFile={vi.fn()}
        multiSelect
        selectedPaths={selected}
        onSelectionChange={(paths) => { selected = paths }}
      />,
    )
    const checkboxes = screen.getAllByRole('checkbox')
    await user.click(checkboxes[0])
    expect(selected).toHaveLength(1)
  })

  it('clicking checked file removes it from selection', async () => {
    let selected = ['src/index.ts']
    const user = userEvent.setup()

    render(
      <FileTree
        items={mockFileTree}
        onSelectFile={vi.fn()}
        multiSelect
        selectedPaths={selected}
        onSelectionChange={(paths) => { selected = paths }}
      />,
    )
    const indexCheckbox = screen.getByRole('checkbox', { name: /index\.ts/i })
    await user.click(indexCheckbox)
    expect(selected).not.toContain('src/index.ts')
  })
})
