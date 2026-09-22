import { ref } from 'vue'
import type {
  InstanceListSortDirection,
  InstanceListSortField,
  WorkflowInstanceListRow,
} from '@/types/workflowInstanceList'

export function useInstanceListSort(defaultField: InstanceListSortField = 'started_at') {
  const sortField = ref<InstanceListSortField | ''>(defaultField)
  const sortDirection = ref<InstanceListSortDirection>('descend')

  function sortOrderParam(): 'asc' | 'desc' | undefined {
    if (!sortField.value || !sortDirection.value) return undefined
    return sortDirection.value === 'ascend' ? 'asc' : 'desc'
  }

  function sortQueryParams(): { sort_field?: string; sort_order?: string } {
    if (!sortField.value || !sortDirection.value) return {}
    if (sortField.value === 'total_amount') return {}
    return {
      sort_field: sortField.value,
      sort_order: sortOrderParam(),
    }
  }

  function onSorterChange(dataIndex: string, direction: InstanceListSortDirection) {
    sortField.value = (dataIndex as InstanceListSortField) || defaultField
    sortDirection.value = direction || 'descend'
  }

  function sortRowsClient(rows: WorkflowInstanceListRow[]): WorkflowInstanceListRow[] {
    if (sortField.value !== 'total_amount' || !sortDirection.value) return rows
    const dir = sortDirection.value === 'ascend' ? 1 : -1
    return [...rows].sort((a, b) => {
      const av = a.total_amount ?? Number.NEGATIVE_INFINITY
      const bv = b.total_amount ?? Number.NEGATIVE_INFINITY
      if (av === bv) return 0
      return av > bv ? dir : -dir
    })
  }

  function sortOrderFor(field: string): InstanceListSortDirection | undefined {
    return sortField.value === field ? sortDirection.value || undefined : undefined
  }

  return {
    sortField,
    sortDirection,
    sortOrderParam,
    sortQueryParams,
    onSorterChange,
    sortRowsClient,
    sortOrderFor,
  }
}
