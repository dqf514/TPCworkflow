import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { clearPrintBodyClasses } from '@/utils/printDocument'
import { resetSessionRedirectFlag } from '@/utils/sessionRedirect'
import { ensureEmbedDesktopQuery, isEmbedDesktopActive } from '@/utils/embedDesktop'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/auth/azure/callback',
      name: 'azure-callback',
      component: () => import('@/views/AzureCallbackView.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      component: () => import('@/layouts/AppLayout.vue'),
      children: [
        { path: '', name: 'dashboard', component: () => import('@/views/DashboardView.vue') },
        { path: 'apply', name: 'apply', component: () => import('@/views/ApplyCatalogView.vue') },
        {
          path: 'apply/start',
          name: 'apply-start',
          component: () => import('@/views/ApplyFlowView.vue'),
        },
        { path: 'tasks', name: 'tasks', component: () => import('@/views/TasksView.vue') },
        {
          path: 'tasks/:id',
          name: 'task-detail',
          component: () => import('@/views/TaskDetailView.vue'),
        },
        {
          path: 'instances/:uuid',
          name: 'instance-detail',
          component: () => import('@/views/InstanceDetailView.vue'),
        },
        {
          path: 'instances',
          name: 'my-instances',
          component: () => import('@/views/MyInstancesView.vue'),
        },
        {
          path: 'leave-calendar',
          name: 'leave-calendar',
          component: () => import('@/views/LeaveCalendarView.vue'),
        },
        {
          path: 'admin/org',
          name: 'admin-org',
          component: () => import('@/views/admin/OrgAdminView.vue'),
          meta: { admin: true },
        },
        {
          path: 'admin/i18n',
          redirect: { name: 'admin-settings', query: { tab: 'i18n' } },
        },
        {
          path: 'admin/form-studio',
          name: 'admin-form-studio',
          component: () => import('@/views/admin/FormStudioView.vue'),
          meta: { admin: true, formStudio: true },
        },
        {
          path: 'admin/workflows',
          redirect: { name: 'admin-form-studio' },
        },
        {
          path: 'admin/users',
          redirect: { name: 'admin-org' },
        },
        {
          path: 'admin/flow-roles',
          redirect: { name: 'admin-org', query: { tab: 'roles' } },
        },
        {
          path: 'admin/sector-monitor',
          name: 'admin-sector-monitor',
          component: () => import('@/views/admin/SectorMonitorView.vue'),
          meta: { admin: true, sectorMonitor: true },
        },
        {
          path: 'admin/finance-export',
          name: 'admin-finance-export',
          component: () => import('@/views/admin/FinanceExportView.vue'),
          meta: { admin: true, financeExport: true },
        },
        {
          path: 'admin/settings',
          name: 'admin-settings',
          component: () => import('@/views/admin/SettingsAdminView.vue'),
          meta: { admin: true },
        },
        {
          path: 'admin/logs',
          name: 'admin-logs',
          component: () => import('@/views/admin/AdminLogsView.vue'),
          meta: { admin: true },
        },
      ],
    },
  ],
})

router.beforeEach(async (to) => {
  const embedRedirect = ensureEmbedDesktopQuery(to)
  if (embedRedirect) return embedRedirect

  const auth = useAuthStore()
  if (!auth.loaded) await auth.fetchMe()
  if (to.meta.public) {
    if (auth.user && to.name === 'login') return { name: 'dashboard', query: { embed: to.query.embed } }
    return true
  }
  if (!auth.user) {
    resetSessionRedirectFlag()
    if (isEmbedDesktopActive(to)) {
      return true
    }
    return { name: 'login', query: { redirect: to.fullPath, reason: 'session_expired' } }
  }
  if (to.meta.admin && !auth.user.is_system_admin) {
    if (to.meta.formStudio && auth.user.can_design_workflow) {
      return true
    }
    if (to.meta.sectorMonitor && auth.user.is_sector_admin && auth.user.can_view_instances) {
      return true
    }
    if (to.meta.financeExport && auth.user.can_export_instances) {
      return true
    }
    return { name: 'dashboard' }
  }
  return true
})

router.afterEach((to, from) => {
  if (from.name === 'instance-detail') {
    clearPrintBodyClasses()
  }
  void import('@/utils/pageViewLog').then(({ reportPageView }) => reportPageView(to))
})

export default router
