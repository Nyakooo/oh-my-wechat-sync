<script setup>
const status = 'Import-first 归档核心已就绪'
</script>

<template>
  <main class="shell">
    <section class="card">
      <p class="eyebrow">WECHAT ARCHIVE</p>
      <h1>微信聊天归档</h1>
      <p class="summary">{{ status }}</p>
      <div class="notice">
        当前版本先支持离线导入与只读归档；真实微信数据来源仍在验证中。
      </div>
    </section>
  </main>
</template>
