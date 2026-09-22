import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  IconCalendar,
  IconCalendarClock,
  IconDashboard,
  IconEdit,
  IconFile,
  IconMindMapping,
  IconSend,
} from '@arco-design/web-vue/es/icon'
import { useAuthStore } from '@/stores/auth'
import { useWorkflowBadgesStore } from '@/stores/workflowBadges'

export const CORE_BOTTOM_TAB_KEYS = [
  'dashboard',
  'apply',
  'my-instances',
  'tasks',
  'leave-calendar',
] as const

export type NavMenuItem = {
  key: string
  label: string
  icon: object
  badge?: number
}

export function useNavMenu() {
  const { t } = useI18n()
  const auth = useAuthStore()
  const badges = useWorkflowBadgesStore()

  const showSectorMonitor = computed(
    () =>
      auth.user?.is_system_admin ||
      (auth.user?.is_sector_admin && auth.user?.can_view_instances),
  )

  const showFinanceExport = computed(
    () => auth.user?.is_system_admin || Boolean(auth.user?.can_export_instances),
  )

  const showStatsGroup = computed(() => showSectorMonitor.value || showFinanceExport.value)

  const showSystemAdmin = computed(() => Boolean(auth.user?.is_system_admin))

  const showFormStudio = computed(
    () => Boolean(auth.user?.is_system_admin || auth.user?.can_design_workflow),
  )

  const showOrg = computed(() => Boolean(auth.user?.is_system_admin))

  const primaryItems = computed((): NavMenuItem[] => {
    const items: NavMenuItem[] = [
      { key: 'dashboard', label: t('menu.dashboard'), icon: IconDashboard },
      { key: 'apply', label: t('menu.apply'), icon: IconSend },
      {
        key: 'leave-calendar',
        label: t('menu.leave_calendar'),
        icon: IconCalendar,
      },
      {
        key: 'my-instances',
        label: t('menu.my_instances'),
        icon: IconFile,
        badge: badges.mineUnreadCount + badges.participatedPendingCount,
      },
      {
        key: 'tasks',
        label: t('menu.tasks'),
        icon: IconCalendarClock,
        badge: badges.todoCount,
      },
    ]
    if (showOrg.value) {
      items.push({ key: 'admin-org', label: t('menu.org_structure'), icon: IconMindMapping })
    }
    if (showFormStudio.value) {
      items.push({ key: 'admin-form-studio', label: t('menu.form_studio'), icon: IconEdit })
    }
    return items
  })

  const bottomBarTabs = computed(() =>
    CORE_BOTTOM_TAB_KEYS.map((key) => primaryItems.value.find((item) => item.key === key)).filter(
      (item): item is NavMenuItem => Boolean(item),
    ),
  )

  const showMoreTab = computed(() => {
    const extraPrimary = primaryItems.value.filter(
      (item) => !(CORE_BOTTOM_TAB_KEYS as readonly string[]).includes(item.key),
    )
    return extraPrimary.length > 0 || showStatsGroup.value || showSystemAdmin.value
  })

  return {
    primaryItems,
    bottomBarTabs,
    showMoreTab,
    showStatsGroup,
    showSystemAdmin,
    showFormStudio,
    showOrg,
    showSectorMonitor,
    showFinanceExport,
  }
}
