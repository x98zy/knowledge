<template>
  <form class="panel-form" @submit.prevent="onSubmit">
    <h2 class="panel-title">登录</h2>
    <p class="panel-subtitle">欢迎回来，请登录你的知识库账号</p>

    <div class="field">
      <input
        v-model="username"
        class="field-input"
        type="text"
        placeholder="用户名"
        required
      />
    </div>

    <div class="field">
      <input
        v-model="password"
        class="field-input"
        type="password"
        placeholder="密码"
        required
      />
    </div>

    <button class="btn" type="submit" :disabled="loading">
      {{ loading ? '登录中...' : '登录' }}
    </button>

    <p class="message error" v-if="error">{{ error }}</p>
    <p class="message success" v-if="success">{{ success }}</p>

    <p class="switch-link">
      还没有账号？
      <a href="#" @click.prevent="$emit('switch')">立即注册</a>
    </p>
  </form>
</template>

<script setup>
import { ref } from 'vue'
import { login } from '../api'

const emit = defineEmits(['switch'])

const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')
const success = ref('')

const onSubmit = async () => {
  error.value = ''
  success.value = ''
  loading.value = true

  try {
    const data = await login(username.value, password.value)
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    success.value = '登录成功，正在跳转...'
    // Redirect to knowledge base home after short delay
    setTimeout(() => {
      window.location.hash = '#/dashboard'
    }, 800)
  } catch (e) {
    if (e.response?.data?.message) {
      error.value = e.response.data.message
    } else {
      error.value = '网络异常，请稍后重试'
    }
  } finally {
    loading.value = false
  }
}
</script>
