import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api, type ApiResponse } from '@/api/client'

export interface WorkflowBadgeSummary {
  todo_count: number
  participated_pending_count: number
  mine_unread_count: number
}

export const useWorkflowBadgesStore = defineStore('workflowBadges', () => {
  const todoCount = ref(0)
  const participatedPendingCount = ref(0)
  const mineUnreadCount = ref(0)
  const loading = ref(false)
  let inflight: Promise<void> | null = null

  /**
   * 刷新待办徽标。
   * 注意：inflight 去重是无条件的 —— 之前 `force` 参数可以绕过它，
   * 导致 AppLayout / TasksView 等处一次交互触发多次重复请求。
   * 语义上「刷新」本来就意味着拉最新数据，不需要额外的 force。
   */
  async function refresh() {
    if (inflight) return inflight
    loading.value = true
    inflight = (async () => {
      try {
        const res = await api.get<ApiResponse<WorkflowBadgeSummary>>('/workflow/tasks/badge-summary')
        if (res.data.ok) {
          todoCount.value = Math.max(0, Number(res.data.data.todo_count) || 0)
          participatedPendingCount.value = Math.max(
            0,
            Number(res.data.data.participated_pending_count) || 0,
          )
          mineUnreadCount.value = Math.max(0, Number(res.data.data.mine_unread_count) || 0)
        }
      } catch {
        todoCount.value = 0
        participatedPendingCount.value = 0
        mineUnreadCount.value = 0
      } finally {
        loading.value = false
        inflight = null
      }
    })()
    return inflight
  }

  function reset() {
    todoCount.value = 0
    participatedPendingCount.value = 0
    mineUnreadCount.value = 0
  }

  return {
    todoCount,
    participatedPendingCount,
    mineUnreadCount,
    loading,
    refresh,
    reset,
  }
})
