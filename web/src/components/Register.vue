<template>
  <form class="panel-form" @submit.prevent="onSubmit">
    <h2 class="panel-title">注册</h2>
    <p class="panel-subtitle">创建你的知识库账号</p>

    <div class="field">
      <input
        v-model="username"
        class="field-input"
        type="text"
        placeholder="用户名（3-50 字符）"
        required
      />
      <span class="field-error" v-if="errors.username">{{ errors.username }}</span>
    </div>

    <div class="field">
      <input
        v-model="email"
        class="field-input"
        type="email"
        placeholder="邮箱"
        required
      />
      <span class="field-error" v-if="errors.email">{{ errors.email }}</span>
    </div>

    <div class="field">
      <input
        v-model="password"
        class="field-input"
        type="password"
        placeholder="密码（至少 8 位，含大小写、数字、特殊字符）"
        required
      />
      <span class="field-error" v-if="errors.password">{{ errors.password }}</span>
    </div>

    <div class="field">
      <input
        v-model="confirm_password"
        class="field-input"
        type="password"
        placeholder="确认密码"
        required
      />
      <span class="field-error" v-if="errors.confirm_password">{{ errors.confirm_password }}</span>
    </div>

    <button class="btn" type="submit" :disabled="loading">
      {{ loading ? '注册中...' : '注册' }}
    </button>

    <p class="message error" v-if="apiError">{{ apiError }}</p>
    <p class="message success" v-if="success">{{ success }}</p>

    <p class="switch-link">
      已有账号？
      <a href="#" @click.prevent="$emit('switch')">立即登录</a>
    </p>
  </form>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { register } from '../api'

const emit = defineEmits(['switch'])

const username = ref('')
const email = ref('')
const password = ref('')
const confirm_password = ref('')
const loading = ref(false)
const apiError = ref('')
const success = ref('')
const errors = reactive({ username: '', email: '', password: '', confirm_password: '' })

function validate() {
  let valid = true
  errors.username = ''
  errors.email = ''
  errors.password = ''
  errors.confirm_password = ''

  if (username.value.length < 3) {
    errors.username = '用户名长度至少 3 个字符'
    valid = false
  }

  const emailRe = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/
  if (!emailRe.test(email.value)) {
    errors.email = '邮箱格式不正确'
    valid = false
  }

  const pw = password.value
  if (pw.length < 8) {
    errors.password = '密码长度至少 8 位'
    valid = false
  } else if (!/[A-Z]/.test(pw) || !/[a-z]/.test(pw) || !/\d/.test(pw) || !/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>/?~`]/.test(pw)) {
    errors.password = '密码必须包含大写字母、小写字母、数字和特殊字符'
    valid = false
  }

  if (password.value !== confirm_password.value) {
    errors.confirm_password = '两次输入的密码不一致'
    valid = false
  }

  return valid
}

const onSubmit = async () => {
  apiError.value = ''
  success.value = ''

  if (!validate()) return

  loading.value = true
  try {
    await register({
      username: username.value,
      email: email.value,
      password: password.value,
      confirm_password: confirm_password.value,
    })
    success.value = '注册成功！请登录'
    setTimeout(() => emit('switch'), 1500)
  } catch (e) {
    if (e.response?.data?.message) {
      apiError.value = e.response.data.message
    } else {
      apiError.value = '网络异常，请稍后重试'
    }
  } finally {
    loading.value = false
  }
}
</script>
