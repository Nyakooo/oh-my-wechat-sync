<script setup>
import { onMounted, onUnmounted, ref } from 'vue'

const accounts = ref([])
const conversations = ref([])
const messages = ref([])
const selectedAccount = ref(null)
const selectedConversation = ref(null)
const searchQuery = ref('')
const searchType = ref('')
const searchFrom = ref('')
const searchTo = ref('')
const searchResults = ref([])
const packageName = ref('')
const syncJob = ref(null)
const syncError = ref('')
const syncTimer = ref(null)
const messageOffset = ref(0)
const hasMoreMessages = ref(false)
const messagePageSize = 100
const loading = ref(false)
const error = ref('')
const health = ref(null)

const request = async (url, options) => {
  const response = await fetch(url, options)
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || `请求失败（${response.status}）`)
  }
  return response.json()
}

const formatTime = (value) => {
  if (!value) return '从未同步'
  return new Date(value).toLocaleString('zh-CN', { dateStyle: 'medium', timeStyle: 'short' })
}

const loadAccounts = async () => {
  loading.value = true
  error.value = ''
  try {
    const [accountData, healthData] = await Promise.all([
      request('/api/v1/accounts'),
      request('/healthz'),
    ])
    accounts.value = accountData
    health.value = healthData
    if (selectedAccount.value) {
      selectedAccount.value = accounts.value.find((item) => item.id === selectedAccount.value.id) || null
    }
  } catch (cause) {
    error.value = cause.message
  } finally {
    loading.value = false
  }
}

const openAccount = async (account) => {
  selectedAccount.value = account
  selectedConversation.value = null
  messages.value = []
  error.value = ''
  try {
    conversations.value = await request(`/api/v1/accounts/${encodeURIComponent(account.id)}/conversations?limit=100`)
  } catch (cause) {
    error.value = cause.message
  }
}

const openConversation = async (conversation) => {
  selectedConversation.value = conversation
  messageOffset.value = 0
  await loadMessages()
}

const loadMessages = async () => {
  error.value = ''
  try {
    messages.value = await request(
      `/api/v1/accounts/${encodeURIComponent(selectedAccount.value.id)}/conversations/${encodeURIComponent(selectedConversation.value.id)}/messages?limit=${messagePageSize}&offset=${messageOffset.value}`,
    )
    hasMoreMessages.value = messages.value.length === messagePageSize
  } catch (cause) {
    error.value = cause.message
  }
}

const changeMessagePage = async (direction) => {
  const nextOffset = messageOffset.value + direction * messagePageSize
  if (nextOffset < 0 || (!hasMoreMessages.value && direction > 0)) return
  messageOffset.value = nextOffset
  await loadMessages()
}

const search = async () => {
  if (!selectedAccount.value || !searchQuery.value.trim()) {
    searchResults.value = []
    return
  }
  try {
    const params = new URLSearchParams({ account_id: selectedAccount.value.id, q: searchQuery.value.trim() })
    if (searchType.value) params.set('message_type', searchType.value)
    if (searchFrom.value) params.set('start_at', String(Date.parse(`${searchFrom.value}T00:00:00`)))
    if (searchTo.value) params.set('end_at', String(Date.parse(`${searchTo.value}T23:59:59.999`)))
    searchResults.value = await request(
      `/api/v1/search?${params.toString()}`,
    )
  } catch (cause) {
    error.value = cause.message
  }
}

const pollSync = async () => {
  if (!syncJob.value) return
  try {
    syncJob.value = await request(`/api/v1/sync/jobs/${encodeURIComponent(syncJob.value.id || syncJob.value.job_id)}`)
    if (['queued', 'running', 'cancel_requested'].includes(syncJob.value.status)) {
      syncTimer.value = setTimeout(pollSync, 350)
    } else {
      await loadAccounts()
    }
  } catch (cause) {
    syncError.value = cause.message
  }
}

const startSync = async () => {
  if (!selectedAccount.value || !packageName.value.trim()) return
  syncError.value = ''
  syncJob.value = null
  try {
    syncJob.value = await request(`/api/v1/accounts/${encodeURIComponent(selectedAccount.value.id)}/sync/import`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ package_name: packageName.value.trim() }),
    })
    await pollSync()
  } catch (cause) {
    syncError.value = cause.message
  }
}

const cancelSync = async () => {
  if (!syncJob.value) return
  try {
    syncJob.value = await request(`/api/v1/sync/jobs/${encodeURIComponent(syncJob.value.job_id || syncJob.value.id)}/cancel`, { method: 'POST' })
    await pollSync()
  } catch (cause) {
    syncError.value = cause.message
  }
}

const openSearchResult = async (result) => {
  let conversation = conversations.value.find((item) => item.id === result.conversation_id)
  if (!conversation) {
    try {
      conversations.value = await request(`/api/v1/accounts/${encodeURIComponent(selectedAccount.value.id)}/conversations?limit=100`)
      conversation = conversations.value.find((item) => item.id === result.conversation_id)
    } catch (cause) {
      error.value = cause.message
      return
    }
  }
  if (conversation) {
    searchResults.value = []
    await openConversation(conversation)
  }
}

onMounted(loadAccounts)
onUnmounted(() => {
  if (syncTimer.value) clearTimeout(syncTimer.value)
})
</script>

<template>
  <main class="shell">
    <header class="topbar">
      <div>
        <p class="eyebrow">WECHAT ARCHIVE / READ-ONLY</p>
        <h1>微信聊天归档</h1>
        <p class="subtitle">手动导入、独立保存，只读浏览。</p>
      </div>
      <button class="quiet-button" type="button" :disabled="loading" @click="loadAccounts">
        {{ loading ? '刷新中…' : '刷新' }}
      </button>
    </header>

    <p v-if="error" class="error" role="alert">{{ error }}</p>

    <section class="overview-grid" aria-label="归档概览">
      <article class="stat-card"><span>归档账号</span><strong>{{ health?.counts?.accounts ?? accounts.length }}</strong></article>
      <article class="stat-card"><span>归档消息</span><strong>{{ health?.counts?.messages ?? 0 }}</strong></article>
      <article class="stat-card stat-card--note"><span>当前模式</span><strong>Import-first</strong></article>
    </section>

    <section class="workspace">
      <aside class="account-panel card">
        <div class="section-heading">
          <div><p class="section-kicker">ACCOUNTS</p><h2>我的账号</h2></div>
          <span class="count-badge">{{ accounts.length }}</span>
        </div>
        <div v-if="!accounts.length" class="empty-state">还没有归档账号。请先通过导入 API 写入一份脱敏导入包。</div>
        <button
          v-for="account in accounts"
          :key="account.id"
          class="account-item"
          :class="{ 'account-item--active': selectedAccount?.id === account.id }"
          type="button"
          @click="openAccount(account)"
        >
          <span class="avatar">{{ account.display_name.slice(0, 1) }}</span>
          <span class="account-copy"><strong>{{ account.display_name }}</strong><small>{{ account.message_count }} 条消息 · {{ formatTime(account.last_sync_at) }}</small></span>
          <span class="status-dot" :class="`status-dot--${account.status}`"></span>
        </button>
      </aside>

      <section class="reader card">
        <div v-if="!selectedAccount" class="reader-empty">
          <span class="reader-mark">◎</span><h2>选择一个账号</h2><p>从左侧打开归档账号，浏览会话和历史消息。</p>
        </div>
        <template v-else>
          <div class="reader-header">
            <div><p class="section-kicker">{{ selectedAccount.display_name }}</p><h2>{{ selectedConversation?.title || '会话列表' }}</h2></div>
            <div class="search-tools">
              <label class="search-box"><span class="sr-only">搜索当前账号</span><input v-model="searchQuery" placeholder="搜索消息" @keyup.enter="search" /><button type="button" @click="search">搜索</button></label>
              <div class="search-filters">
                <select v-model="searchType" aria-label="消息类型"><option value="">所有类型</option><option value="text">文本</option><option value="image">图片</option><option value="file">文件</option></select>
                <input v-model="searchFrom" type="date" aria-label="开始日期" />
                <input v-model="searchTo" type="date" aria-label="结束日期" />
              </div>
            </div>
          </div>

          <form class="sync-panel" @submit.prevent="startSync">
            <div><p class="section-kicker">MANUAL IMPORT</p><strong>手动同步导入包</strong><small>只接受服务器 imports 目录下的相对包名</small></div>
            <input v-model="packageName" placeholder="例如：account-a-export" :disabled="['queued', 'running', 'cancel_requested'].includes(syncJob?.status)" />
            <button type="submit" :disabled="!packageName.trim() || ['queued', 'running', 'cancel_requested'].includes(syncJob?.status)">{{ syncJob?.status === 'running' ? '同步中…' : '开始同步' }}</button>
            <button v-if="['queued', 'running', 'cancel_requested'].includes(syncJob?.status)" type="button" class="cancel-button" @click="cancelSync">取消</button>
            <span v-if="syncJob" class="sync-status">{{ syncJob.status }} · {{ syncJob.phase || 'queued' }}</span>
            <span v-if="syncJob?.error_message" class="sync-error">{{ syncJob.error_message }}</span>
            <span v-if="syncJob?.stats_json" class="sync-status">统计：{{ syncJob.stats_json }}</span>
            <span v-if="syncError" class="sync-error">{{ syncError }}</span>
          </form>

          <div v-if="searchResults.length" class="search-results">
            <p class="section-kicker">SEARCH RESULTS · {{ searchResults.length }}</p>
            <button v-for="result in searchResults" :key="result.id" type="button" class="result-item" @click="openSearchResult(result)"><span>{{ result.content }}</span><small>{{ formatTime(result.source_created_at) }}</small></button>
          </div>

          <div v-else class="reader-columns">
            <nav class="conversation-list" aria-label="会话列表">
              <p v-if="!conversations.length" class="empty-state">该账号暂无会话。</p>
              <button v-for="conversation in conversations" :key="conversation.id" class="conversation-item" :class="{ 'conversation-item--active': selectedConversation?.id === conversation.id }" type="button" @click="openConversation(conversation)">
                <strong>{{ conversation.title || conversation.source_chat_id }}</strong><small>{{ conversation.message_count }} 条消息</small>
              </button>
            </nav>
            <div class="message-list">
              <p v-if="!messages.length" class="empty-state">选择一个会话查看消息。</p>
              <article v-for="message in messages" :key="message.id" class="message-item">
                <div class="message-meta"><strong>{{ message.is_self ? '我' : (message.sender_display_name || '未知联系人') }}</strong><time>{{ formatTime(message.source_created_at) }}</time></div>
                <p>{{ message.content || `[${message.type}]` }}</p>
                <div v-if="message.attachments.length" class="attachment-list">
                  <a v-for="attachment in message.attachments" :key="attachment.id" class="attachment-note" :href="`/api/v1/accounts/${encodeURIComponent(selectedAccount.id)}/attachments/${encodeURIComponent(attachment.id)}/content`" target="_blank" rel="noopener">{{ attachment.original_name || attachment.kind }}</a>
                </div>
              </article>
              <div v-if="messages.length" class="pager">
                <button type="button" :disabled="messageOffset === 0" @click="changeMessagePage(-1)">上一页</button>
                <span>第 {{ Math.floor(messageOffset / messagePageSize) + 1 }} 页</span>
                <button type="button" :disabled="!hasMoreMessages" @click="changeMessagePage(1)">下一页</button>
              </div>
            </div>
          </div>
        </template>
      </section>
    </section>

    <footer>真实微信来源仍在验证中 · 当前界面只浏览已导入归档</footer>
  </main>
</template>
