<template>
  <div class="min-h-screen flex items-center justify-center">
    <a-spin tip="正在完成 Office 365 登录…" />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { api, type ApiResponse } from '@/api/client'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

onMounted(async () => {
  const code = route.query.code as string
  const state = route.query.state as string
  if (code) {
    await api.get('/auth/azure/callback', { params: { code, state } })
    await auth.fetchMe()
  }
  router.replace('/')
})
</script>
